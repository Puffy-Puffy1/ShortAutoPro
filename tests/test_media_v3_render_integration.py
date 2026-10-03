import base64,json,subprocess,tempfile,unittest,struct,zlib
from pathlib import Path
from unittest.mock import patch
import media_acquisition_v3, render_engine_v2
from media_v3.providers import ProviderAdapter,ProviderRegistry,ProviderStatus

def make_png():
    w=h=64; raw=b"".join(b"\x00"+b"".join(bytes(((x*4)%256,(y*4)%256,180)) for x in range(w)) for y in range(h))
    def chunk(t,d): return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
    return b"\x89PNG\\r\\n\x1a\\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b"")

class FixtureProvider(ProviderAdapter):
    name="fixture"
    def __init__(self,fixture): self.fixture=Path(fixture)
    def status(self): return ProviderStatus(True)
    def search(self,query): return [{"provider":"fixture","kind":"image","id":"fixture-1","url":"file://fixture","local_path":str(self.fixture),"description":"roman soldier"}]

class V3RenderIntegration(unittest.TestCase):
    def test_v3_manifest_to_real_ffmpeg_render(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); sid="INTEGRATION_01"; fixture=base/"fixture.png"; fixture.write_bytes(make_png())
            for p in ("roteiros","imagens","audios","videos","manifests"): (base/p).mkdir(parents=True,exist_ok=True)
            (base/"roteiros"/f"scene_map_{sid}.json").write_text(json.dumps({"scenes":[{"scene_id":"scene_01","scene":1,"query":"roman soldier","words":1}]}),encoding="utf-8")
            (base/"roteiros"/f"pro_edit_plan_{sid}.json").write_text(json.dumps({"scenes":[{"scene_id":"scene_01","pace_multiplier":1.0,"zoom_start":1.0,"zoom_end":1.02,"pan":"center","cut_style":"editorial_cut","transition_duration":0}]}),encoding="utf-8")
            ass=base/"videos"/f"short_{sid}.ass"
            ass.write_text("""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,80,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,Integration test
""",encoding="utf-8")
            audio=base/"audios"/f"short_{sid}.mp3"
            p=subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","lavfi","-i","sine=frequency=440:duration=2","-c:a","aac","-b:a","96k",str(audio)],capture_output=True,text=True,check=False,timeout=60)
            self.assertEqual(p.returncode,0,p.stderr)
            media_acquisition_v3.BASE=base; render_engine_v2.BASE=base
            provider=FixtureProvider(fixture)
            with patch.object(media_acquisition_v3,"MediaAcquisitionV3",lambda base: __import__("media_v3.acquisition",fromlist=["MediaAcquisitionV3"]).MediaAcquisitionV3(base,ProviderRegistry([provider]))):
                manifest=media_acquisition_v3.build_manifest(sid)
            self.assertEqual(manifest["schema_version"],"media-manifest-v2")
            with patch.dict("os.environ",{"SAP_RENDER_V2_BACKEND":"ffmpeg","SAP_RENDER_V2_CRF":"28"},clear=False), patch.object(render_engine_v2.sys,"argv",["render_engine_v2.py","--short-id",sid]):
                rc=render_engine_v2.main()
            self.assertEqual(rc,0)
            final=base/"videos"/f"short_v6_{sid}.mp4"
            self.assertTrue(final.is_file()); self.assertGreater(final.stat().st_size,1000)
            probe=subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type,width,height,codec_name","-of","json",str(final)],capture_output=True,text=True,check=True)
            streams=json.loads(probe.stdout)["streams"]
            self.assertTrue(any(s.get("codec_type")=="video" for s in streams))
            self.assertTrue(any(s.get("codec_type")=="audio" for s in streams))

if __name__=="__main__": unittest.main()
