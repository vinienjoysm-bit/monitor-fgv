import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HISTORICO = "history.json"
TELEFONE_ALVO = "0800 591 3078"

def buscar_projetos():
    print("🔍 Buscando projetos...")
    projetos = []
    try:
        url_base = "https://conhecimento.fgv.br/busca"
        headers = {"User-Agent": "Mozilla/5.0"}
        for pagina in range(1, 4):
            params = {"keys": "concurso", "page": pagina}
            resp = requests.get(url_base, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/concurso" in href or "/processo-seletivo" in href or "/exame" in href:
                    url_proj = href if href.startswith("http") else f"https://conhecimento.fgv.br{href}"
                    try:
                        r = requests.get(url_proj, headers=headers, timeout=10)
                        if TELEFONE_ALVO in r.text:
                            nome = link.get_text(strip=True)[:100]
                            
                            # Tenta pegar a data
                            s = BeautifulSoup(r.text, "html.parser")
                            data_mod = "Data não encontrada"
                            tag = s.find("time") or s.find("span", class_="date") or s.find("p", class_="date")
                            if tag and tag.get_text(strip=True):
                                data_mod = tag.get_text(strip=True)

                            # Tenta pegar a descrição (primeiro parágrafo ou meta description)
                            descricao = ""
                            meta_desc = s.find("meta", attrs={"name": "description"})
                            if meta_desc:
                                descricao = meta_desc["content"].strip()
                            else:
                                p = s.find("p")
                                if p:
                                    descricao = p.get_text(strip=True)[:300]

                            projetos.append({
                                "id": url_proj.split("/")[-1],
                                "nome": nome,
                                "url": url_proj,
                                "ultima_mod": data_mod,
                                "descricao": descricao
                            })
                    except:
                        continue
            if not projetos:
                break
    except:
        pass

    # Lista de emergência caso o site mude
    if not projetos:
        projetos = [
            {"id": "trf5", "nome": "TRF 5ª Região - Juiz Federal", "url": "https://conhecimento.fgv.br/concursos/trf5juiz", "ultima_mod": "2026-02-10", "descricao": "Concurso Público para o Tribunal Regional Federal da 5ª Região."},
            {"id": "enare", "nome": "ENARE", "url": "https://enare2026.conhecimento.fgv.br", "ultima_mod": "2026-02-10", "descricao": "Exame Nacional de Residência."},
            {"id": "cfc", "nome": "Exame de Suficiência CFC", "url": "https://conhecimento.fgv.br/busca", "ultima_mod": "2026-02-10", "descricao": "Exame de Suficiência do Conselho Federal de Contabilidade."},
            {"id": "eqt", "nome": "Exame de Qualificação Técnica", "url": "https://conhecimento.fgv.br/busca", "ultima_mod": "2026-02-10", "descricao": "Exame de Qualificação Técnica."}
        ]
    return projetos

def enviar_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        # Parse_mode HTML para negrito
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

def main():
    print("Iniciando verificação...")
    novos = buscar_projetos()
    antigos = []
    try:
        with open(HISTORICO, "r") as f:
            antigos = json.load(f).get("projetos", [])
    except:
        pass

    ids_novos = {p["id"] for p in novos}
    ids_antigos = {p["id"] for p in antigos}
    adicionados = [p for p in novos if p["id"] not in ids_antigos]
    removidos = [p for p in antigos if p["id"] not in ids_novos]
    antigos_map = {p["id"]: p for p in antigos}
    alterados = [p for p in novos if p["id"] in antigos_map and p["ultima_mod"] != antigos_map[p["id"]].get("ultima_mod")]

    if not adicionados and not removidos and not alterados:
        enviar_telegram("✅ Nenhuma alteração identificada desde a última verificação.")
    else:
        msg = "🚨 <b>ALTERAÇÕES DETECTADAS!</b>\n"
        for p in adicionados:
            msg += f"🆕 <b>NOVO:</b> {p['nome']}\n"
            msg += f"📅 <b>Data:</b> {p['ultima_mod']}\n"
            if p['descricao']:
                msg += f"📝 <b>Descrição:</b> {p['descricao']}\n"
            msg += f"🔗 {p['url']}\n\n"
        for p in removidos:
            msg += f"❌ <b>REMOVIDO:</b> {p['nome']}\n\n"
        for p in alterados:
            msg += f"🔄 <b>ALTERADO:</b> {p['nome']}\n"
            msg += f"📅 <b>Data:</b> {p['ultima_mod']}\n"
            if p['descricao']:
                msg += f"📝 <b>Descrição:</b> {p['descricao']}\n"
            msg += f"🔗 {p['url']}\n\n"
        enviar_telegram(msg)

    with open(HISTORICO, "w") as f:
        json.dump({"projetos": novos, "ultima": datetime.now().isoformat()}, f)

if __name__ == "__main__":
    main()
