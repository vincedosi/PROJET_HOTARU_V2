# Backoffice HOTARU — Gestion centralisée (tabs SaaS-ready)
# Onglets : Utilisateurs | Workspaces | Accès

import streamlit as st

from core.session_keys import get_current_user_email, is_admin


def render_backoffice_tab(auth, db):
    """Backoffice complet : Utilisateurs, Workspaces, Accès — en tabs."""
    if not is_admin():
        st.warning("Accès réservé aux administrateurs.")
        return
    if not auth or not db:
        st.error("Backoffice : auth ou base non disponible.")
        return

    st.markdown("## Backoffice")
    st.caption("Gestion centralisée des utilisateurs, workspaces et droits d'accès.")

    tab_users, tab_workspaces, tab_access = st.tabs([
        "Utilisateurs",
        "Workspaces",
        "Accès par workspace",
    ])

    with tab_users:
        _render_users_tab(auth)

    with tab_workspaces:
        _render_workspaces_tab(db)

    with tab_access:
        _render_access_tab(auth, db)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Utilisateurs
# ═══════════════════════════════════════════════════════════════════════════════
def _render_users_tab(auth):
    users = auth.list_users()

    st.markdown("### Liste des utilisateurs")
    if not users:
        st.info("Aucun utilisateur enregistré.")
    else:
        header = st.columns([3, 1.5, 1.5, 1.5, 2])
        header[0].markdown("**Email**")
        header[1].markdown("**Rôle**")
        header[2].markdown("**Créé le**")
        header[3].markdown("**Dernier login**")
        header[4].markdown("**Actions**")
        st.divider()

        for i, u in enumerate(users):
            email = u.get("email", "")
            role = u.get("role", "user")
            created_at = u.get("created_at", "")
            last_login = u.get("last_login", "")

            cols = st.columns([3, 1.5, 1.5, 1.5, 2])
            with cols[0]:
                st.text(email)
            with cols[1]:
                new_role = st.selectbox(
                    "Rôle", ["user", "admin"],
                    index=0 if role == "user" else 1,
                    key=f"bo_role_{i}_{email}",
                    label_visibility="collapsed",
                )
            with cols[2]:
                st.caption(created_at[:10] if created_at else "—")
            with cols[3]:
                st.caption(last_login[:16] if last_login else "—")
            with cols[4]:
                c1, c2 = st.columns(2)
                with c1:
                    if new_role != role and st.button("Appliquer", key=f"bo_apply_{i}"):
                        try:
                            auth.update_user_role(email, new_role)
                            st.toast(f"Rôle de {email} mis à jour.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e)[:200])
                with c2:
                    if st.button("Supprimer", key=f"bo_del_{i}"):
                        me = (get_current_user_email() or "").strip().lower()
                        if email.strip().lower() == me:
                            st.error("Impossible de supprimer votre propre compte.")
                        else:
                            try:
                                auth.delete_user(email)
                                st.toast(f"{email} supprimé.")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e)[:200])

    st.markdown("---")
    st.markdown("### Ajouter un utilisateur")
    with st.form("bo_add_user"):
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


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Workspaces
# ═══════════════════════════════════════════════════════════════════════════════
def _render_workspaces_tab(db):
    all_ws = db.list_all_workspaces() or []

    st.markdown("### Workspaces existants")
    if not all_ws:
        st.info("Aucun workspace trouvé. Créez-en un ci-dessous.")
    else:
        for i, ws in enumerate(all_ws):
            cols = st.columns([3, 2, 1])
            with cols[0]:
                st.markdown(f"**{ws}**")
            with cols[1]:
                new_name = st.text_input(
                    "Nouveau nom", value=ws,
                    key=f"bo_ws_rename_{i}",
                    label_visibility="collapsed",
                )
            with cols[2]:
                changed = new_name.strip() and new_name.strip() != ws
                if changed and st.button("Renommer", key=f"bo_ws_rename_btn_{i}"):
                    if hasattr(db, "rename_workspace"):
                        try:
                            ok = db.rename_workspace(ws, new_name.strip())
                            if ok:
                                st.toast(f"Workspace renommé : {ws} → {new_name.strip()}")
                                st.rerun()
                            else:
                                st.error("Échec du renommage.")
                        except Exception as e:
                            st.error(str(e)[:200])
                    else:
                        st.error("Renommage non disponible pour ce backend.")
        st.divider()

    # Créer un workspace
    st.markdown("### Créer un workspace")
    with st.form("bo_create_ws"):
        ws_name = st.text_input("Nom du workspace", placeholder="Mon Projet")
        if st.form_submit_button("Créer"):
            name = (ws_name or "").strip()
            if not name:
                st.error("Nom requis.")
            elif name in all_ws:
                st.error(f"Le workspace « {name} » existe déjà.")
            else:
                if hasattr(db, "create_workspace"):
                    try:
                        db.create_workspace(name)
                        st.toast(f"Workspace « {name} » créé.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e)[:200])
                else:
                    st.error("Création non disponible pour ce backend.")

    # Déplacer des sauvegardes entre workspaces
    st.markdown("---")
    st.markdown("### Déplacer des sauvegardes")
    if len(all_ws) < 2:
        st.info("Au moins 2 workspaces requis pour déplacer des sauvegardes.")
    else:
        source_ws = st.selectbox("Workspace source", all_ws, key="bo_move_source")
        target_options = [w for w in all_ws if w != source_ws]
        target_ws = st.selectbox("Workspace cible", target_options, key="bo_move_target")

        saves = []
        if hasattr(db, "list_workspace_saves_admin"):
            saves = db.list_workspace_saves_admin(source_ws) or []
        if not saves:
            st.info(f"Aucune sauvegarde dans « {source_ws} ».")
        else:
            save_labels = [
                f"{s.get('nom_site', 'Save')} — {s.get('user_email', '?')} ({s.get('created_at', '')})"
                for s in saves
            ]
            selected = st.multiselect("Sauvegardes à déplacer", save_labels, key="bo_move_sel")
            if selected and st.button("Déplacer", type="primary", key="bo_move_btn"):
                ids = [saves[save_labels.index(lbl)].get("save_id") for lbl in selected]
                if hasattr(db, "move_saves_to_workspace"):
                    try:
                        count = db.move_saves_to_workspace(ids, target_ws)
                        st.toast(f"{count} sauvegarde(s) déplacée(s) vers « {target_ws} ».")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e)[:200])
                else:
                    st.error("Déplacement non disponible pour ce backend.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Accès par workspace
# ═══════════════════════════════════════════════════════════════════════════════
def _render_access_tab(auth, db):
    users = auth.list_users()
    all_ws = db.list_all_workspaces() or []

    if not users:
        st.info("Aucun utilisateur.")
        return
    if not all_ws:
        st.info("Aucun workspace. Créez-en un dans l'onglet Workspaces.")
        return

    st.markdown("### Accès par utilisateur")
    st.caption("Cochez les workspaces accessibles. Vide = accès à tous.")

    for i, u in enumerate(users):
        email = u.get("email", "")
        role = u.get("role", "user")
        current = set(db.get_user_workspaces(email))

        st.markdown(f"**{email}** `{role}`")
        max_cols = min(len(all_ws), 4)
        cols = st.columns(max_cols)
        selected = []
        for j, ws in enumerate(all_ws):
            with cols[j % max_cols]:
                if st.checkbox(ws, value=ws in current, key=f"bo_acc_{i}_{ws}"):
                    selected.append(ws)

        if st.button("Enregistrer accès", key=f"bo_acc_save_{i}"):
            try:
                db.set_user_workspaces(email, selected)
                st.toast(f"Accès mis à jour pour {email}.")
                st.rerun()
            except Exception as e:
                st.error(str(e)[:200])
        st.divider()
