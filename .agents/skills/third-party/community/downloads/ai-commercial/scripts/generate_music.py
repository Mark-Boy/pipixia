#!/usr/bin/env python3
"""
Procedural music generator for ai-commercial.

Self-contained — vendors social-video's NumPy synth so this skill works standalone
without requiring social-video to be installed. The vendored function generates
cinematic + ambient music styles natively; other styles fall back to cinematic.

Outputs MP3 to $PROJECT_DIR/generated/music/bed.mp3 by default.

Usage:
  python3 generate_music.py --style cinematic --duration 60
  python3 generate_music.py --style ambient --duration 45 --out custom.mp3

Auto-invoked by make_commercial.py if a music bed isn't already on disk.

Source: extracted from social-video's make_video.py (function generate_music).
To sync upstream improvements, re-extract from
~/.claude/commands/social-video/scripts/make_video.py lines 636-761.
"""
import argparse, os, pathlib, subprocess, sys, tempfile, wave
import numpy as np

ROOT = pathlib.Path(os.environ.get("PROJECT_DIR", os.getcwd())).expanduser().resolve()
DEFAULT_OUT = ROOT / "generated/music/bed.mp3"

SR = 44100  # sample rate

# ═══════════════════════════════════════════════════════════════
# Vendored from social-video's make_video.py — generate_music()
# ═══════════════════════════════════════════════════════════════
def generate_music(duration, out_path, style="cinematic"):
    total = int(SR * duration)
    track = np.zeros(total)
    t = np.linspace(0, duration, total)

    if style == "cinematic":
        bpm = 75; beat = SR*60/bpm
        p1 = int(total*0.42); p2 = int(total*0.80)

        # Build phase: deep drones + pads + rising tension
        for freq, amp, ls in [(32.7,.07,.06),(65.41,.05,.08),(49.0,.04,.1)]:
            env = np.linspace(0.2,1.0,p1)**0.7
            lfo = 0.96+0.04*np.sin(2*np.pi*ls*t[:p1])
            track[:p1] += amp*env*np.sin(2*np.pi*freq*t[:p1])*lfo

        for i,freq in enumerate([130.81,155.56,196.0,233.08,293.66]):
            amp = (0.018-i*0.002)*np.linspace(0.1,1,p1)**0.8
            vib = 1+0.003*np.sin(2*np.pi*(4.5+i*0.3)*t[:p1])
            track[:p1] += amp*np.sin(2*np.pi*freq*vib*t[:p1])

        # Tension ticks
        for i in range(0,p1,int(beat*2)):
            n=int(SR*0.02); end=min(i+n,p1)
            track[i:end]+=(0.02+0.1*i/p1)*np.random.randn(end-i)*np.exp(-100*np.linspace(0,0.02,end-i))

        # Rising sweep
        rise=np.linspace(0,0.04,p1)**1.5*np.random.randn(p1)
        for j in range(1,p1): rise[j]=0.95*rise[j-1]+0.05*rise[j]
        track[:p1]+=rise

        # Timpani roll
        rs=int(p1*0.6)
        for i in range(16):
            pos=rs+int((p1-rs)*(i/16)**1.5)
            if pos>=p1: break
            n=int(SR*0.15); end=min(pos+n,p1)
            t_h=np.linspace(0,0.15,end-pos)
            track[pos:end]+=(0.08+0.25*i/16)*np.sin(2*np.pi*80*t_h)*np.exp(-20*t_h)

        # Impact
        imp=p1-int(SR*0.15)
        if imp>0:
            n=int(SR*0.8); end=min(imp+n,total)
            ti=np.linspace(0,0.8,end-imp)
            track[imp:end]+=0.7*np.sin(2*np.pi*60*np.exp(-5*ti)*ti)*np.exp(-3*ti)
            track[imp:end]+=0.3*np.random.randn(end-imp)*np.exp(-6*ti)

        # Drop: heavy kicks, bass, snares, hats, chords, lead
        dl=p2-p1
        for i in range(0,dl,int(beat)):
            s=p1+i; ch=min(int(beat),total-s)
            if ch<=0: break
            sc=np.ones(ch); dk=min(int(SR*0.08),ch)
            sc[:dk]=np.linspace(0.15,1,dk)**2
            track[s:s+ch]+=0.20*np.sin(2*np.pi*65.41*t[s:s+ch])*sc

        for i in range(0,dl,int(beat)):
            s=p1+i; n=int(SR*0.3); end=min(s+n,total)
            tk=np.linspace(0,0.3,end-s)
            track[s:end]+=0.65*np.sin(2*np.pi*300*np.exp(-50*tk)*tk)*np.exp(-10*tk)
            track[s:end]+=0.3*np.sin(2*np.pi*60*tk)*np.exp(-6*tk)

        for i in range(int(beat),dl,int(beat*2)):
            s=p1+i; n=int(SR*0.15); end=min(s+n,total)
            ts=np.linspace(0,0.15,end-s)
            track[s:end]+=0.28*np.random.randn(end-s)*np.exp(-22*ts)

        for i in range(0,dl,int(beat/4)):
            s=p1+i
            if s>=total: break
            n=int(SR*0.025); end=min(s+n,total)
            vol=0.16 if (i//int(beat/4))%4==0 else 0.08
            track[s:end]+=vol*np.random.randn(end-s)*np.exp(-100*np.linspace(0,0.025,end-s))

        for i in range(0,dl,int(beat*2)):
            s=p1+i
            for freq,amp in [(261.63,.10),(311.13,.09),(392.0,.09),(523.25,.07)]:
                n=int(SR*0.35); end=min(s+n,total); a=end-s
                w=amp*np.sin(2*np.pi*freq*np.linspace(0,0.35,a))
                env=np.ones(a)
                att=min(int(SR*0.003),a); dec=min(int(SR*0.1),a)
                env[:att]=np.linspace(0,1,att); env[-dec:]=np.linspace(1,0,dec)
                track[s:end]+=w*env

        # Lead melody
        melody=[(523.25,.5),(659.25,.5),(783.99,1.0),(659.25,.5),(523.25,1.0),(783.99,.5),(1046.5,1.5)]
        pos=p1+int(beat*2)
        for freq,db in melody:
            n=int(beat*db); end=min(pos+n,p2)
            if pos>=p2: break
            a=end-pos; tm=np.linspace(0,db*60/bpm,a)
            vib=1+0.005*np.sin(2*np.pi*5.5*tm)
            lead=0.06*np.sin(2*np.pi*freq*vib*tm)
            env=np.ones(a)
            env[:min(int(SR*0.02),a)]=np.linspace(0,1,min(int(SR*0.02),a))
            env[-min(int(SR*0.15),a):]=np.linspace(1,0,min(int(SR*0.15),a))
            track[pos:end]+=lead*env; pos=end

        # Resolution
        rl=total-p2; re=np.linspace(1,0,rl)**0.5
        for freq,amp in [(130.81,.07),(164.81,.06),(196.0,.06),(261.63,.04)]:
            track[p2:]+=amp*re*np.sin(2*np.pi*freq*t[p2:])
        track[p2:]+=0.06*re*np.sin(2*np.pi*65.41*t[p2:])

    elif style == "ambient":
        bpm=85; beat=SR*60/bpm
        for freq,amp in [(65.41,.10),(77.78,.08),(98.00,.07)]:
            lfo=0.97+0.03*np.sin(2*np.pi*0.2*t)
            track+=amp*np.sin(2*np.pi*freq*t)*lfo
        for start in range(0,total-SR,int(beat*2)):
            for freq in [261.63,311.13,392.00]:
                n=int(SR*0.25); w=0.07*np.sin(2*np.pi*freq*np.linspace(0,0.25,n))
                env=np.concatenate([np.linspace(0,1,int(SR*0.01)),np.ones(n-int(SR*0.06)),np.linspace(1,0,int(SR*0.05))])[:n]
                end=min(start+n,total)
                track[start:end]+=(w*env)[:end-start]

    # Master
    track[:int(SR*1.5)]*=np.linspace(0,1,int(SR*1.5))
    track[-int(SR*3):]*=np.linspace(1,0,int(SR*3))
    peak=np.max(np.abs(track))
    if peak>0: track=np.clip(track/peak*0.5,-1,1)

    with wave.open(out_path,"w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((track*32767).astype(np.int16).tobytes())



def wav_to_mp3(wav_path: pathlib.Path, mp3_path: pathlib.Path):
    """Convert WAV → MP3 with ffmpeg."""
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(wav_path),
        "-codec:a", "libmp3lame", "-b:a", "192k",
        str(mp3_path),
    ], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="cinematic",
                    choices=["cinematic", "ambient", "upbeat", "electronic", "acoustic"],
                    help="Music style. cinematic and ambient are implemented; others fall back to cinematic.")
    ap.add_argument("--duration", type=float, required=True,
                    help="Length in seconds. The bed will be looped during commercial composition.")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help=f"Output MP3 path (default: $PROJECT_DIR/generated/music/bed.mp3)")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite if output exists.")
    args = ap.parse_args()

    out_path = pathlib.Path(args.out).expanduser().resolve()
    if out_path.exists() and not args.force:
        print(f"Music bed already exists at {out_path} — use --force to overwrite. Skipping.")
        return

    style = args.style
    if style not in ("cinematic", "ambient"):
        print(f"Note: style \'{style}\' not yet implemented in the vendored synth — falling back to \'cinematic\'.")
        style = "cinematic"

    print(f"Generating {args.duration:.1f}s of \'{style}\' music ({SR}Hz)...")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = pathlib.Path(tmp.name)
    try:
        generate_music(args.duration, str(wav_path), style=style)
        wav_to_mp3(wav_path, out_path)
        print(f"Saved: {out_path} ({out_path.stat().st_size // 1024} KB)")
    finally:
        try:
            wav_path.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
