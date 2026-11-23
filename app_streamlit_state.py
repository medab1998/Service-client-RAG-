"""
Interface Streamlit — version avec state.

Streamlit ne garde plus de copie de la conversation : l'historique, les
actions en attente et le journal sont lus directement dans l'état du graphe
(app.get_state).

uv run streamlit run app_streamlit_state.py
"""

import uuid
from pathlib import Path

import streamlit as st

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent_boutique_state import app
from outils_base import creer_base


st.set_page_config(
    page_title="Service client boutique",
    page_icon="🛒"
)


# ---------- Initialisation ----------

st.cache_resource(creer_base)()  # une seule fois au démarrage du serveur

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())  # seule information gardée par Streamlit

config = {
    "configurable": {
        "thread_id": st.session_state.thread_id
    }
}

snapshot = app.get_state(config)  # photo de l'état du graphe

etat = snapshot.values  # {messages, journal, nb_appels_llm}

actions = (
    snapshot.interrupts[0].value
    if snapshot.interrupts
    else None
)  # graphe en pause ?
# ---------- Barre latérale ----------

with st.sidebar:

    st.header("🛒 Boutique")
    st.caption("Agent LangGraph : RAG + SQL + validation humaine")

    if st.button("Nouvelle conversation", use_container_width=True):

        creer_base()  # remet les commandes dans leur état initial

        st.session_state.clear()  # nouveau thread_id = nouvel état vide

        st.rerun()

    with st.expander("Graphe de l'agent"):  # schéma des nœuds et des arêtes

        st.image(str(Path(__file__).parent / "images.jfif"))

    st.subheader("État du graphe")

    st.metric(
        "Appels au LLM",
        etat.get("nb_appels_llm", 0)
    )

    st.markdown("**Journal des validations**")

    st.markdown(
        "\n".join(f"- {l}" for l in etat.get("journal", []))
        or "_aucune action sensible_"
    )

    st.subheader("Questions à essayer")

    st.markdown(
        "- Quels sont les délais de livraison ?\n"
        "- Où en est la commande 1002 ?\n"
        "- Annule ma commande 1001\n"
        "- J'ai reçu la commande 1003 mais la souris ne marche pas, "
        "je peux la retourner ?\n"
        "- Je veux retourner la commande 1004, le casque ne me plaît "
        "plus."
    )
    # ---------- Conversation (lue dans l'état) ----------

st.title("Service client")

for m in etat.get("messages", []):

    if m.type == "human":
        st.chat_message("user").markdown(m.text)

    elif m.type == "ai" and m.text:
        # On ignore les messages qui ne font qu'appeler des outils
        st.chat_message("assistant").markdown(m.text)
        # ---------- Envoi au graphe ----------

envoi_au_graphe = None  # question du client ou décision du responsable
# None : rien à envoyer


# Validation humaine : le graphe est en pause
if actions:

    st.markdown(
        "**Validation requise :**\n\n"
        + "\n".join(f"- `{a}`" for a in actions)
    )

    col1, col2 = st.columns(2)

    if col1.button("✅ Valider", use_container_width=True):
        envoi_au_graphe = Command(resume="oui")

    if col2.button("❌ Refuser", use_container_width=True):
        envoi_au_graphe = Command(resume="non")


# Saisie d'une question par le client
question = st.chat_input(
    "Votre question...",
    disabled=bool(actions)
)

if question:

    st.chat_message("user").markdown(question)

    envoi_au_graphe = {
        "messages": [HumanMessage(question)]
    }
    # ---------- Exécution du graphe ----------

if envoi_au_graphe is not None:

    with st.spinner("Thought..."):

        app.invoke(
            envoi_au_graphe,
            config
        )  # le résultat est enregistré dans l'état

    st.rerun()  # réaffichage à partir du nouvel état