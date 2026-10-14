import os

import httpx
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="Job Copilot", layout="wide")


def call(method: str, path: str, **kw):
    r = httpx.request(method, f"{API}{path}", timeout=600, **kw)
    r.raise_for_status()
    return r.json()


st.title("Job Copilot — validation humaine")

with st.sidebar:
    st.header("Pipeline")
    if st.button("1. Ingérer les offres"):
        st.json(call("POST", "/ingest"))
    if st.button("2. Matcher avec mon profil"):
        res = call("POST", "/match")
        st.caption(f"Coût du run : {res['usage']['cost_usd']} $")

tab_matches, tab_review = st.tabs(["Offres matchées", "À valider"])

with tab_matches:
    for m in call("GET", "/matches"):
        with st.expander(f"{m['score']}/100 — {m['title']} @ {m['company'] or '?'}"):
            st.write(m["rationale"])
            c1, c2 = st.columns(2)
            c1.markdown("**Points forts**\n" + "\n".join(f"- {x}" for x in m["strengths"]))
            c2.markdown("**Manques**\n" + "\n".join(f"- {x}" for x in m["gaps"]))
            if m["url"]:
                st.link_button("Voir l'offre", m["url"])
            if st.button("Générer un brouillon", key=f"gen{m['offer_id']}"):
                call("POST", f"/offers/{m['offer_id']}/draft")
                st.success("Brouillon créé — onglet « À valider ».")

with tab_review:
    for d in call("GET", "/drafts"):
        rate = d["unsupported_rate"]
        with st.expander(
            f"Brouillon #{d['id']} — non supporté : {rate:.0%} — {d['attempts']} essai(s)"
        ):
            letter = st.text_area(
                "Lettre", d["content"]["cover_letter"], height=320, key=f"l{d['id']}"
            )
            highlights = st.text_area(
                "Points forts CV", "\n".join(d["content"]["cv_highlights"]), key=f"h{d['id']}"
            )
            bad = [c for c in d["grounding"]["claims"] if not c["supported"]]
            if bad:
                st.warning("Affirmations non ancrées dans ton CV :")
                for c in bad:
                    st.write(f"- {c['text']}")
            reason = st.text_input("Motif (si rejet)", key=f"r{d['id']}")
            a, b, c = st.columns(3)
            if a.button("Approuver", key=f"a{d['id']}"):
                call("POST", f"/drafts/{d['id']}/review", json={"action": "approve"})
                st.rerun()
            if b.button("Enregistrer mes modifs", key=f"e{d['id']}"):
                edited = {"cover_letter": letter, "cv_highlights": highlights.splitlines()}
                call(
                    "POST",
                    f"/drafts/{d['id']}/review",
                    json={"action": "edit", "edited_content": edited},
                )
                st.rerun()
            if c.button("Rejeter", key=f"x{d['id']}"):
                call(
                    "POST", f"/drafts/{d['id']}/review", json={"action": "reject", "reason": reason}
                )
                st.rerun()
