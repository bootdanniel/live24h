import os
import time
import requests
from flask import Flask, Response

app = Flask(__name__)

URL_LIVE_TXT = "https://raw.githubusercontent.com/bootdanniel/live24h/main/url_live.txt"
CACHE_TTL = 30  # segundos

_cache = {"url": None, "ts": 0}


def get_live_url():
    agora = time.time()
    if _cache["url"] and (agora - _cache["ts"]) < CACHE_TTL:
        return _cache["url"]
    try:
        # ?v=timestamp forca bypass do cache do CDN do GitHub
        r = requests.get(URL_LIVE_TXT + "?v=" + str(int(agora)), timeout=10)
        if r.status_code == 200:
            url = r.text.strip()
            _cache["url"] = url
            _cache["ts"] = agora
            print(f"[PROXY] URL atualizada: {url}")
            return url
    except Exception as e:
        print(f"[PROXY] Erro ao ler url_live.txt: {e}")
    return _cache["url"]


@app.route("/stream.txt")
@app.route("/stream.m3u8")
@app.route("/")
def proxy():
    live_url = get_live_url()
    if not live_url:
        return "Live offline (sem URL no GitHub)", 503

    try:
        r = requests.get(live_url, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return f"Erro na live: {r.status_code}", 502

        base_url = live_url.rsplit("/", 1)[0] + "/"
        linhas = r.text.split("\n")
        saida = []
        for linha in linhas:
            l = linha.strip()
            if l.endswith(".ts") or l.endswith(".m3u8"):
                if not l.startswith("http"):
                    saida.append(base_url + l)
                    continue
            saida.append(linha)

        return Response(
            "\n".join(saida),
            mimetype="application/vnd.apple.mpegurl",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache, no-store, must-revalidate"
            }
        )
    except Exception as e:
        return f"Erro: {e}", 500


@app.route("/")
def home():
    live_url = get_live_url()
    return f"Proxy OK. Live atual: {live_url or 'indefinida'}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"[PROXY] Iniciando na porta {port}")
    app.run(host="0.0.0.0", port=port)
