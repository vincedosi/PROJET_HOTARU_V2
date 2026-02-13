# =============================================================================
# HOTARU API - FastAPI
# Routes pour exposer la logique métier (modules/core) sans Streamlit
# =============================================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="HOTARU API", version="1.0.0")


# =============================================================================
# SCHEMAS
# =============================================================================
class AuthorityRequest(BaseModel):
    entity_name: str
    website_url: str
    competitors: Optional[list[str]] = None


# =============================================================================
# ROUTES
# =============================================================================
@app.post("/audit/authority")
def audit_authority(payload: AuthorityRequest):
    """
    Calcule l'AI Authority Index d'une entité.
    Retourne le score global, le détail par pilier, l'interprétation et les recommandations.
    """
    try:
        from modules.audit.authority_score import compute_authority_score

        result = compute_authority_score(
            entity_name=payload.entity_name,
            website_url=payload.website_url,
            competitors=payload.competitors or [],
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}
