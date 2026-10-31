import json
import unittest

import httpx

from backend.services import bluebubbles_reader as bb


def stand_in(seen, password="s3cret", broken_chat=None):
    """A tiny stand-in for a BlueBubbles server. Records every request it gets."""
    chats = [
        {"guid": "iMessage;-;+15550001", "chatIdentifier": "+15550001", "displayName": "",
         "participants": [{"address": "+15550001"}]},
        {"guid": "iMessage;+;chat9", "chatIdentifier": "chat9", "displayName": "Climbing crew",
         "participants": [{"address": "a@x.com"}, {"address": "b@x.com"}]},
        {"guid": "iMessage;-;empty", "chatIdentifier": "empty", "displayName": "", "participants": []},
    ]
    messages = {  # newest first, like sort=DESC
        "iMessage;-;+15550001": [
            {"guid": "m3", "text": "did you see my last text?", "isFromMe": False, "dateCreated": 1_789_500_000_000},
            {"guid": "m2", "text": "   ", "isFromMe": False, "dateCreated": 1_789_400_000_000},
            {"guid": "m1", "text": "saturday still on?", "isFromMe": False, "dateCreated": 1_789_300_000_000},
        ],
        "iMessage;+;chat9": [
            {"guid": "g2", "text": "see you there", "isFromMe": True, "dateCreated": 1_789_450_000_000},
            {"guid": "g1", "text": "7 works", "isFromMe": False, "dateCreated": 1_789_440_000_000},
        ],
        "iMessage;-;empty": [{"guid": "e1", "text": "", "isFromMe": True, "dateCreated": 1_789_000_000_000}],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, dict(request.url.params)))
        if request.url.params.get("guid") != password:
            return httpx.Response(401, json={"status": 401, "message": "Unauthorized"})
        path = request.url.path
        if path == "/api/v1/ping":
            return httpx.Response(200, json={"status": 200, "message": "Ping received!", "data": "pong"})
        if path == "/api/v1/chat/query":
            body = json.loads(request.content)
            return httpx.Response(200, json={"status": 200, "data": chats[: body["limit"]]})
        if path.startswith("/api/v1/chat/") and path.endswith("/message"):
            guid = path[len("/api/v1/chat/"):-len("/message")]
            if guid == broken_chat:
                return httpx.Response(500, json={"status": 500, "message": "boom"})
            return httpx.Response(200, json={"status": 200, "data": messages.get(guid, [])})
        return httpx.Response(404, json={"status": 404, "message": "no such route"})

    return httpx.Client(transport=httpx.MockTransport(handler))


class BlueBubblesTests(unittest.TestCase):
    def test_addresses_are_cleaned_up(self):
        self.assertEqual(bb.normalize_base_url("192.168.1.20:1234"), "http://192.168.1.20:1234")
        self.assertEqual(bb.normalize_base_url(" https://mac.example.com/ "), "https://mac.example.com")
        for bad in ("", "   ", "ftp://x.com", "http://"):
            with self.assertRaises(ValueError):
                bb.normalize_base_url(bad)

    def test_connection_check_reports_success_and_wrong_password(self):
        seen = []
        ok = bb.check_connection("mac.local:1234", "s3cret", client=stand_in(seen))
        self.assertTrue(ok["accessible"])
        self.assertEqual(seen[0][1], "/api/v1/ping")
        bad = bb.check_connection("mac.local:1234", "nope", client=stand_in([]))
        self.assertFalse(bad["accessible"])
        self.assertIn("password", bad["error"])

    def test_unreachable_server_gets_a_plain_message(self):
        def refuse(request):
            raise httpx.ConnectError("refused", request=request)
        client = httpx.Client(transport=httpx.MockTransport(refuse))
        status = bb.check_connection("10.0.0.9:1234", "x", client=client)
        self.assertFalse(status["accessible"])
        self.assertIn("Could not reach", status["error"])

    def test_threads_match_what_the_local_reader_produces(self):
        seen = []
        result = bb.read_threads("mac.local:1234", "s3cret", max_threads=10, max_messages=20, client=stand_in(seen))
        self.assertTrue(result["ok"], result["error"])
        threads = {t["thread_id"]: t for t in result["threads"]}
        self.assertEqual(len(threads), 2, "a chat with no text is left out")

        dm = threads["iMessage;-;+15550001"]
        self.assertEqual(dm["contact_name"], "+15550001")
        self.assertEqual(dm["handles"], ["+15550001"])
        self.assertEqual([m["text"] for m in dm["messages"]], ["saturday still on?", "did you see my last text?"])
        self.assertTrue(dm["needs_response_estimate"])
        self.assertEqual(dm["latest_message"], "did you see my last text?")
        self.assertIsNotNone(dm["latest_at"])
        self.assertIsNone(dm["latest_at"].tzinfo, "naive UTC, like chat.db")

        crew = threads["iMessage;+;chat9"]
        self.assertEqual(crew["contact_name"], "Climbing crew")
        self.assertEqual(crew["handles"], ["a@x.com", "b@x.com"])
        self.assertFalse(crew["needs_response_estimate"], "you spoke last")
        for t in result["threads"]:
            for key in ("thread_id", "contact_name", "handles", "latest_message", "latest_at", "messages"):
                self.assertIn(key, t)
            for m in t["messages"]:
                self.assertEqual(set(m), {"message_id", "is_from_me", "text", "created_at", "service"})

    def test_it_only_reads_and_always_sends_the_password_as_guid(self):
        seen = []
        bb.read_threads("mac.local:1234", "s3cret", client=stand_in(seen))
        self.assertTrue(seen)
        for method, path, params in seen:
            self.assertEqual(params.get("guid"), "s3cret")
            self.assertNotIn("send", path.lower())
            self.assertNotIn("/text", path.lower())
            self.assertTrue((method, path) == ("POST", "/api/v1/chat/query") or method == "GET", (method, path))

    def test_a_failing_chat_fails_the_sync_with_a_message_not_a_crash(self):
        result = bb.read_threads("mac.local:1234", "s3cret", client=stand_in([], broken_chat="iMessage;+;chat9"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["threads"], [])
        self.assertIn("error", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
