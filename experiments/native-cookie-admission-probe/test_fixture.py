"""HTTP fixture responses and received cookies are observable independently."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from fixture import make_server

class FixtureTests(unittest.TestCase):
    def test_seed_attributes_and_no_credential_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            server=make_server(Path(tmp),0,tls=False)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                for case,attribute in [('httponly','HttpOnly'),('offpath','Path=/hidden/'),('partitioned','Partitioned')]:
                    client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
                    client.request('GET',f'/seed?run=test&case={case}',headers={'Cookie':'t28a_public=sentinel'})
                    response=client.getresponse()
                    self.assertIn(attribute,response.headers['Set-Cookie'])
                    self.assertNotIn(b'sentinel',response.read());client.close()
                rows=[json.loads(line) for line in (Path(tmp)/'requests.jsonl').read_text().splitlines()]
                self.assertEqual(len(rows),3)
                self.assertTrue(all(row['cookie']=='t28a_public=sentinel' for row in rows))
            finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
