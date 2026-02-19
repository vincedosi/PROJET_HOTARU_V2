# Backoffice HOTARU — Gestion centralisée (tabs SaaS-ready)
# Onglets : Utilisateurs | Workspaces | Accès

import logging
import streamlit as st

from core.session_keys import get_current_user_email, is_admin

logger = logging.getLogger(__name__)


def render_backoffice_tab(auth, db):
    """Backoffice complet : Utilisateurs, Workspaces, Accès — en tabs."""
    if not is_admin():
        st.warning("Accès réservé aux administrateurs.")
        return
    if not auth or not db:
        logger.error("Backoffice: auth=%s db=%s — un des deux est None", type(auth).__name__ if auth else None, type(db).__name__ if db else None)
        st.error("Backoffice : auth ou base non disponible.")
        return

    logger.info("Backoffice ouvert par %s (backend db=%s)", get_current_user_email(), type(db).__name__)

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
    logger.debug("Chargement liste utilisateurs...")
    users = auth.list_users()
    logger.info("list_users → %d utilisateur(s)", len(users) if users else 0)

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
                        logger.info("Changement rôle: %s → %s (par %s)", email, new_role, get_current_user_email())
                        try:
                            auth.update_user_role(email, new_role)
                            logger.info("Rôle de %s mis à jour → %s OK", email, new_role)
                            st.toast(f"Rôle de {email} mis à jour.")
                            st.rerun()
                        except Exception as e:
                            logger.error("Échec changement rôle %s → %s: %s", email, new_role, e)
                            st.error(str(e)[:200])
                with c2:
                    if st.button("Supprimer", key=f"bo_del_{i}"):
                        me = (get_current_user_email() or "").strip().lower()
                        if email.strip().lower() == me:
                            st.error("Impossible de supprimer votre propre compte.")
                        else:
                            logger.info("Suppression utilisateur: %s (par %s)", email, get_current_user_email())
                            try:
                                auth.delete_user(email)
                                logger.info("Utilisateur %s supprimé OK", email)
                                st.toast(f"{email} supprimé.")
                                st.rerun()
                            except Exception as e:
                                logger.error("Échec suppression %s: %s", email, e)
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
                logger.info("Création utilisateur: %s (rôle=%s, par %s)", new_email.strip(), new_role, get_current_user_email())
                try:
                    auth.register(new_email.strip(), new_password, role=new_role)
                    logger.info("Utilisateur %s créé OK (rôle=%s)", new_email.strip(), new_role)
                    st.toast(f"Utilisateur {new_email} créé.")
                    st.rerun()
                except ValueError as e:
                    logger.warning("Création utilisateur %s refusée: %s", new_email.strip(), e)
                    st.error(str(e))
                except Exception as e:
                    logger.error("Échec création utilisateur %s: %s", new_email.strip(), e)
                    st.error(str(e)[:200])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Workspaces
# ═══════════════════════════════════════════════════════════════════════════════
def _render_workspaces_tab(db):
    logger.debug("Chargement liste workspaces...")
    all_ws = db.list_all_workspaces() or []
    logger.info("list_all_workspaces → %d workspace(s): %s", len(all_ws), all_ws)

    st.markdown("### Workspaces existants")
    if not all_ws:
        st.info("Aucun workspace trouvé. Créez-en un ci-dessous.")
    else:
        for i, ws in enumerate(all_ws):
            cols = st.columns([3, 2, 1, 1])
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
                    logger.info("Renommage workspace: '%s' → '%s' (par %s)", ws, new_name.strip(), get_current_user_email())
                    if hasattr(db, "rename_workspace"):
                        try:
                            ok = db.rename_workspace(ws, new_name.strip())
                            logger.info("rename_workspace('%s', '%s') → %s", ws, new_name.strip(), ok)
                            if ok:
                                st.toast(f"Workspace renommé : {ws} → {new_name.strip()}")
                                st.rerun()
                            else:
                                st.error("Échec du renommage.")
                        except Exception as e:
                            logger.error("Échec renommage workspace '%s' → '%s': %s", ws, new_name.strip(), e)
                            st.error(str(e)[:200])
                    else:
                        logger.warning("rename_workspace non disponible sur %s", type(db).__name__)
                        st.error("Renommage non disponible pour ce backend.")
            with cols[3]:
                delete_key = f"bo_ws_delete_confirm_{i}"
                if st.session_state.get(delete_key):
                    pass
                else:
                    if st.button("Supprimer", key=f"bo_ws_delete_btn_{i}", type="secondary"):
                        st.session_state[delete_key] = True
                        st.rerun()

        for i, ws in enumerate(all_ws):
            delete_key = f"bo_ws_delete_confirm_{i}"
            if st.session_state.get(delete_key):
                saves_in = []
                if hasattr(db, "list_workspace_saves_admin"):
                    saves_in = db.list_workspace_saves_admin(ws)
                st.warning(
                    f"**Supprimer le workspace « {ws} » ?**\n\n"
                    f"{'Ce workspace contient **' + str(len(saves_in)) + ' sauvegarde(s)** qui seront déplacées vers « Non classé ».' if saves_in else 'Ce workspace est vide.'}\n\n"
                    f"Cette action est **irréversible**."
                )
                other_ws = [w for w in all_ws if w != ws]
                move_target = "Non classé"
                if saves_in and other_ws:
                    move_target = st.selectbox(
                        "Déplacer les sauvegardes vers :",
                        ["Non classé"] + other_ws,
                        key=f"bo_ws_delete_move_{i}",
                    )
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Confirmer la suppression", key=f"bo_ws_delete_yes_{i}", type="primary"):
                        logger.info("Suppression workspace '%s' confirmée (move_to='%s') par %s", ws, move_target, get_current_user_email())
                        if hasattr(db, "delete_workspace"):
                            try:
                                result = db.delete_workspace(ws, move_saves_to=move_target)
                                logger.info("delete_workspace('%s') → %s", ws, result)
                                st.toast(f"Workspace « {ws} » supprimé. {result.get('saves_moved', 0)} sauvegarde(s) déplacée(s).")
                                st.session_state.pop(delete_key, None)
                                st.rerun()
                            except Exception as e:
                                logger.error("delete_workspace('%s') EXCEPTION: %s", ws, e, exc_info=True)
                                st.error(f"Erreur : {str(e)[:200]}")
                        else:
                            st.error("Suppression non disponible pour ce backend.")
                with col_no:
                    if st.button("Annuler", key=f"bo_ws_delete_no_{i}"):
                        st.session_state.pop(delete_key, None)
                        st.rerun()

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
                logger.warning("Tentative création workspace en double: '%s'", name)
                st.error(f"Le workspace « {name} » existe déjà.")
            else:
                logger.info("Création workspace: '%s' (par %s, db=%s)", name, get_current_user_email(), type(db).__name__)
                if hasattr(db, "create_workspace"):
                    try:
                        ok = db.create_workspace(name)
                        logger.info("create_workspace('%s') → %s", name, ok)
                        if ok:
                            st.toast(f"Workspace « {name} » créé.")
                            st.rerun()
                        else:
                            logger.error("create_workspace('%s') a retourné False", name)
                            st.error("Échec de la création du workspace.")
                    except ValueError as e:
                        logger.warning("create_workspace('%s') ValueError: %s", name, e)
                        st.error(str(e))
                    except Exception as e:
                        logger.error("create_workspace('%s') Exception: %s", name, e, exc_info=True)
                        st.error(f"Erreur : {str(e)[:200]}")
                else:
                    logger.warning("create_workspace non disponible sur %s", type(db).__name__)
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
            logger.debug("list_workspace_saves_admin('%s')...", source_ws)
            saves = db.list_workspace_saves_admin(source_ws) or []
            logger.info("list_workspace_saves_admin('%s') → %d save(s)", source_ws, len(saves))
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
                logger.info("Déplacement saves %s → '%s' (par %s)", ids, target_ws, get_current_user_email())
                if hasattr(db, "move_saves_to_workspace"):
                    try:
                        count = db.move_saves_to_workspace(ids, target_ws)
                        logger.info("move_saves_to_workspace(%s, '%s') → %d déplacée(s)", ids, target_ws, count)
                        st.toast(f"{count} sauvegarde(s) déplacée(s) vers « {target_ws} ».")
                        st.rerun()
                    except Exception as e:
                        logger.error("Échec déplacement saves %s → '%s': %s", ids, target_ws, e, exc_info=True)
                        st.error(str(e)[:200])
                else:
                    logger.warning("move_saves_to_workspace non disponible sur %s", type(db).__name__)
                    st.error("Déplacement non disponible pour ce backend.")

    # Supprimer des sauvegardes
    st.markdown("---")
    st.markdown("### Supprimer des sauvegardes")
    del_ws_list = db.list_all_workspaces() or []
    if not del_ws_list:
        st.info("Aucun workspace.")
    else:
        del_ws = st.selectbox("Workspace", del_ws_list, key="bo_del_save_ws")
        del_saves = []
        if hasattr(db, "list_workspace_saves_admin"):
            del_saves = db.list_workspace_saves_admin(del_ws) or []

        if not del_saves:
            st.info(f"Aucune sauvegarde dans « {del_ws} ».")
        else:
            del_labels = [
                f"{s.get('nom_site', 'Save')} — {s.get('user_email', '?')} ({s.get('created_at', '')[:16]})"
                for s in del_saves
            ]
            del_selected = st.multiselect(
                f"Sauvegardes à supprimer ({len(del_saves)} au total)",
                del_labels, key="bo_del_save_sel",
            )

            if del_selected:
                del_confirm_key = "bo_del_save_confirm"
                if st.session_state.get(del_confirm_key):
                    st.error(
                        f"**Confirmer la suppression de {len(del_selected)} sauvegarde(s) ?**\n\n"
                        f"Cette action est **irréversible**. Les données seront définitivement effacées de la base."
                    )
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Oui, supprimer définitivement", key="bo_del_save_yes", type="primary"):
                            ids = [del_saves[del_labels.index(lbl)].get("save_id") for lbl in del_selected]
                            logger.info("Suppression saves %s (par %s)", ids, get_current_user_email())
                            if hasattr(db, "delete_saves_bulk"):
                                try:
                                    count = db.delete_saves_bulk(ids)
                                    logger.info("delete_saves_bulk → %d supprimée(s)", count)
                                    st.toast(f"{count} sauvegarde(s) supprimée(s) définitivement.")
                                    st.session_state.pop(del_confirm_key, None)
                                    st.rerun()
                                except Exception as e:
                                    logger.error("delete_saves_bulk EXCEPTION: %s", e, exc_info=True)
                                    st.error(f"Erreur : {str(e)[:200]}")
                            elif hasattr(db, "delete_save"):
                                try:
                                    count = 0
                                    for sid in ids:
                                        if db.delete_save(sid):
                                            count += 1
                                    st.toast(f"{count} sauvegarde(s) supprimée(s).")
                                    st.session_state.pop(del_confirm_key, None)
                                    st.rerun()
                                except Exception as e:
                                    logger.error("delete_save EXCEPTION: %s", e, exc_info=True)
                                    st.error(f"Erreur : {str(e)[:200]}")
                            else:
                                st.error("Suppression non disponible pour ce backend.")
                    with col_no:
                        if st.button("Annuler", key="bo_del_save_no"):
                            st.session_state.pop(del_confirm_key, None)
                            st.rerun()
                else:
                    if st.button(f"Supprimer {len(del_selected)} sauvegarde(s)", type="secondary", key="bo_del_save_btn"):
                        st.session_state[del_confirm_key] = True
                        st.rerun()


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
        logger.debug("get_user_workspaces('%s') → %s", email, current)

        st.markdown(f"**{email}** `{role}`")
        max_cols = min(len(all_ws), 4)
        cols = st.columns(max_cols)
        selected = []
        for j, ws in enumerate(all_ws):
            with cols[j % max_cols]:
                if st.checkbox(ws, value=ws in current, key=f"bo_acc_{i}_{ws}"):
                    selected.append(ws)

        if st.button("Enregistrer accès", key=f"bo_acc_save_{i}"):
            logger.info("Enregistrement accès: %s → %s (par %s)", email, selected, get_current_user_email())
            try:
                db.set_user_workspaces(email, selected)
                logger.info("set_user_workspaces('%s', %s) OK", email, selected)
                st.toast(f"Accès mis à jour pour {email}.")
                st.rerun()
            except Exception as e:
                logger.error("Échec set_user_workspaces('%s', %s): %s", email, selected, e, exc_info=True)
                st.error(str(e)[:200])
        st.divider()
