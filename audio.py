#!/usr/bin/env python3
"""Piper TTS with profile speech direction and loudness-safe output."""
import json,math,os,shutil,subprocess,tempfile
from datetime import date,datetime
from pathlib import Path
from typing import Any
from subprocess_guard import check_output_group, run_group
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve();SHORT_ID=os.getenv("SHORT_ID",date.today().isoformat());R=BASE/"roteiros";ROTEIRO=R/f"short_{SHORT_ID}.txt";SPEECH=R/f"speech_{SHORT_ID}.txt";SPEECH_PLAN=R/f"speech_{SHORT_ID}.json";AUDIO_DIR=BASE/"audios";VOICE_DIR=BASE/"piper"/"voice";AUDIO_DIR.mkdir(parents=True,exist_ok=True);MP3=AUDIO_DIR/f"short_{SHORT_ID}.mp3";MODEL=os.getenv("PIPER_MODEL","pt_BR-faber-medium").strip() or "pt_BR-faber-medium";MODEL_FILE=VOICE_DIR/f"{MODEL}.onnx";MODEL_ARG=str(MODEL_FILE) if MODEL_FILE.is_file() else MODEL;REPORT=BASE/"reports"/"evolution"/f"audio_{SHORT_ID}.json"
def bounded(name,default,low,high):
 try:v=float(os.getenv(name,str(default)))
 except Exception:v=float(default)
 if not math.isfinite(v):v=float(default)
 return max(low,min(high,v))
TARGET_LUFS=bounded("SAP_AUDIO_TARGET_LUFS",-14,-24,-10);TRUE_PEAK_DB=bounded("SAP_AUDIO_TRUE_PEAK_DB",-1.5,-3,-0.5);LRA=bounded("SAP_AUDIO_LRA",7,1,20)
def fail(msg):raise RuntimeError(msg)
def atomic_json(path:Path,payload:Any):
 path.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(prefix=f".{path.name}.",suffix=".tmp",dir=str(path.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(payload,f,ensure_ascii=False,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
  os.replace(t,path)
 except Exception:
  try:os.unlink(t)
  except OSError:pass
  raise
def read_plan()->list[dict[str,Any]]:
 try:d=json.loads(SPEECH_PLAN.read_text(encoding="utf-8"));chunks=d.get("chunks",[]) if isinstance(d,dict) else [];return [x for x in chunks if isinstance(x,dict) and str(x.get("text","")).strip()]
 except Exception:return []
def piper_raw(text:str,dest:Path,env:dict[str,str])->None:
 try:run_group(["piper","-m",MODEL_ARG,"-f",str(dest),"--",text],env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=180)
 except subprocess.TimeoutExpired:fail("Piper excedeu 180 segundos")
 except subprocess.CalledProcessError as exc:fail(f"Piper falhou ({exc.returncode}): {(exc.stderr or '')[-700:]}")
 if not dest.is_file() or dest.stat().st_size<=0:fail("Piper não produziu RAW válido")
def audio_duration(path:Path)->float:
 raw=check_output_group(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True,stderr=subprocess.DEVNULL,timeout=30).strip();v=float(raw)
 if not math.isfinite(v) or v<5:fail(f"duração de áudio inválida: {v}")
 return v
def render_segmented(chunks:list[dict[str,Any]],work:Path,env:dict[str,str])->Path:
 wavs=[]
 for i,ch in enumerate(chunks,1):
  raw=work/f"chunk_{i:02d}.raw";wav=work/f"chunk_{i:02d}.wav";piper_raw(str(ch.get("text","")),raw,env);tempo=bounded_value(ch.get("tempo"),1.0,0.90,1.10);pause=max(0,min(700,int(ch.get("pause_ms",150) or 150)))/1000
  filt=f"atempo={tempo:.4f},aresample=44100,apad=pad_dur={pause:.3f}"
  run_group(["ffmpeg","-y","-loglevel","error","-f","f32le","-ar","22050","-ac","1","-i",str(raw),"-af",filt,"-ar","44100","-ac","1","-c:a","pcm_s16le",str(wav)],check=True,timeout=120);wavs.append(wav)
 concat=work/"chunks.txt";concat.write_text("".join("file '"+str(p).replace("'","'\\''")+"'\n" for p in wavs),encoding="utf-8");combined=work/"speech.wav";run_group(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),"-c:a","pcm_s16le",str(combined)],check=True,timeout=120);return combined
def bounded_value(value,default,low,high):
 try:v=float(value)
 except Exception:v=float(default)
 if not math.isfinite(v):v=float(default)
 return max(low,min(high,v))
def render_single(text:str,work:Path,env:dict[str,str])->Path:
 raw=work/"speech.raw";wav=work/"speech.wav";piper_raw(text,raw,env);run_group(["ffmpeg","-y","-loglevel","error","-f","f32le","-ar","22050","-ac","1","-i",str(raw),"-ar","44100","-ac","1","-c:a","pcm_s16le",str(wav)],check=True,timeout=120);return wav
def main()->int:
 source=SPEECH if SPEECH.is_file() else ROTEIRO
 if not source.is_file():print(f"ERRO: roteiro/speech não encontrado: {source}");return 1
 text=source.read_text(encoding="utf-8").strip()
 if not text or len(text)>20000:print("ERRO: texto TTS vazio ou excessivo");return 1
 if shutil.which("piper") is None or shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:print("ERRO: Piper/FFmpeg/ffprobe ausente");return 1
 if not VOICE_DIR.is_dir():print(f"ERRO: pasta de voz Piper ausente: {VOICE_DIR}");return 1
 env=os.environ.copy();env["PIPER_VOICE_PATH"]=str(VOICE_DIR);chunks=read_plan();work=Path(tempfile.mkdtemp(prefix=f"sap_tts_{SHORT_ID}_",dir=str(AUDIO_DIR)))
 print("\n================================\nGERANDO VOZ COM PIPER - 3.2\nDYNAMIC SPEECH + LOUDNESS\n================================");print(f"Modelo: {MODEL}\nChunks dirigidos: {len(chunks) if chunks else 0}\nMaster de voz: {TARGET_LUFS:.1f} LUFS | TP {TRUE_PEAK_DB:.1f} dB")
 try:
  wav=render_segmented(chunks,work,env) if chunks else render_single(text,work,env);tmp=work/"final.mp3";loud=f"loudnorm=I={TARGET_LUFS:.1f}:TP={TRUE_PEAK_DB:.1f}:LRA={LRA:.1f}";run_group(["ffmpeg","-y","-loglevel","error","-i",str(wav),"-af",loud,"-ar","44100","-ac","1","-codec:a","libmp3lame","-b:a","160k",str(tmp)],check=True,timeout=180);dur=audio_duration(tmp);os.replace(tmp,MP3)
 except Exception as exc:print(f"ERRO AUDIO: {exc}");return 1
 finally:shutil.rmtree(work,ignore_errors=True)
 report={"short_id":SHORT_ID,"generated_at":datetime.now().astimezone().isoformat(timespec="seconds"),"model":MODEL,"speech_directed":source==SPEECH,"dynamic_chunks":len(chunks),"duration_seconds":round(dur,3),"mastering":{"filter":"loudnorm","target_lufs":TARGET_LUFS,"true_peak_db":TRUE_PEAK_DB,"lra":LRA,"bitrate":"160k","sample_rate":44100,"channels":1},"status":"PASS"}
 try:atomic_json(REPORT,report)
 except Exception as exc:print(f"AVISO relatório: {exc}")
 print(f"\nÁUDIO PIPER GERADO | {dur:.2f}s\n{MP3}\n");return 0
if __name__=="__main__":raise SystemExit(main())
