# Engine package
from .master_handler import MasterDataHandler, MasterData
from .dynamic_handler import DynamicDataHandler
from .template_builder import TemplateBuilder

__all__ = ['MasterDataHandler', 'MasterData', 'DynamicDataHandler', 'TemplateBuilder']
```

5. Commit

**Ensuite, vérifie aussi que ces fichiers `__init__.py` existent :**

- `core/__init__.py` (vide ou avec imports)
- `modules/__init__.py` (vide ou avec imports)
- `engine/__init__.py` ← **C'est celui qui manque !**

---

## 📂 Structure finale attendue :
```
projet_hotaru_v2/
├── app.py
├── core/
│   ├── __init__.py          ← Doit exister
│   ├── scraping.py
│   ├── auth.py
│   └── database.py
├── engine/
│   ├── __init__.py          ← 🔥 C'EST CELUI-CI QUI MANQUE !
│   ├── master_handler.py
│   ├── dynamic_handler.py
│   └── template_builder.py
├── modules/
│   ├── __init__.py          ← Doit exister
│   ├── audit_geo.py
│   └── home.py
