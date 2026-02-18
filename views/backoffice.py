# Backoffice HOTARU — Gestion des droits (visible uniquement aux admins)

import streamlit as st

from core.session_keys import get_current_user_email, is_admin


def render_backoffice_tab(auth, db):
    """Affiche l’onglet Backoffice (auth et db fournis par app.py)."""
    if not is_admin():
        st.warning("Accès réservé aux administrateurs.")
        return
    if not auth or not db:
        st.error("Backoffice : auth ou base non disponible.")
        return

    st.markdown("## Backoffice / Gestion des droits")
    st.caption("Utilisateurs, rôles et accès par workspace.")

    # ——— Liste des utilisateurs ———
    users = auth.list_users()
    if not users:
        st.info("Aucun utilisateur.")
    else:
        st.markdown("### Utilisateurs")
        for i, u in enumerate(users):
            email = u.get("email", "")
            role = u.get("role", "user")
            created_at = u.get("created_at", "")
            last_login = u.get("last_login", "")
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
            with col1:
                st.text(email)
            with col2:
                new_role = st.selectbox(
                    "Rôle",
                    ["user", "admin"],
                    index=0 if role == "user" else 1,
                    key=f"role_{i}_{email}",
                    label_visibility="collapsed",
                )
            with col3:
                st.caption(created_at[:10] if created_at else "")
            with col4:
                st.caption(last_login[:16] if last_login else "")
            with col5:
                if new_role != role:
                    if st.button("Appliquer rôle", key=f"apply_{i}"):
                        try:
                            auth.update_user_role(email, new_role)
                            st.toast(f"Rôle de {email} mis à jour.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e)[:200])
                if st.button("Supprimer", key=f"del_{i}"):
                    if email.strip().lower() == (get_current_user_email() or "").strip().lower():
                        st.error("Vous ne pouvez pas supprimer votre propre compte.")
                    else:
                        try:
                            auth.delete_user(email)
                            st.toast(f"Utilisateur {email} supprimé.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e)[:200])
            with st.expander(f"Accès workspaces — {email}", key=f"ws_{i}"):
                all_ws = db.list_all_workspaces() or []
                current = set(db.get_user_workspaces(email))
                selected = []
                for w in all_ws:
                    if st.checkbox(w, value=w in current, key=f"wscb_{i}_{w}"):
                        selected.append(w)
                if st.button("Enregistrer accès", key=f"wssave_{i}"):
                    try:
                        db.set_user_workspaces(email, selected)
                        st.toast(f"Accès enregistré pour {email}.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e)[:200])
            st.divider()

    # ——— Ajouter un utilisateur ———
    st.markdown("### Ajouter un utilisateur")
    with st.form("backoffice_add_user"):
        new_email = st.text_input("Email", placeholder="user@example.com")
        new_password = st.text_input("Mot de passe", type="password")
        new_role = st.selectbox("Rôle", ["user", "admin"])
        if st.form_submit_button("Créer"):
            if not new_email or not new_password:
                st.error("Email et mot de passe requis.")
            else:
                try:
                    auth.register(new_email.strip(), new_password, role=new_role)
                    st.toast(f"Utilisateur {new_email} créé.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(str(e)[:200])
