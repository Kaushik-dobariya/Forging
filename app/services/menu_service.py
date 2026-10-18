from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from app.models.menu import MenuItem, MenuLocation
from app.models.page import CMSPage
from app.core.logging import logger


class MenuService:
    """Service layer for dynamic navigation menus (header & footer) with submenus."""

    def get_menu_tree(
        self, db: Session, location: str = "header", enabled_only: bool = True
    ) -> List[MenuItem]:
        """
        Retrieves root menu items for a specific location along with their child items,
        sorted by display_order.
        """
        query = (
            db.query(MenuItem)
            .options(
                joinedload(MenuItem.page),
                joinedload(MenuItem.children).joinedload(MenuItem.page),
            )
            .filter(MenuItem.location == location, MenuItem.parent_id.is_(None))
        )
        if enabled_only:
            query = query.filter(MenuItem.is_enabled == True)

        items = query.order_by(MenuItem.display_order.asc(), MenuItem.id.asc()).all()

        # If enabled_only, filter children in memory to ensure only enabled children show
        if enabled_only:
            for item in items:
                item.active_children = [c for c in item.children if c.is_enabled]
        else:
            for item in items:
                item.active_children = item.children

        return items

    def list_all_items(
        self, db: Session, location: Optional[str] = None
    ) -> List[MenuItem]:
        """Returns all menu items flattened, ordered by location, parent, and display_order."""
        query = db.query(MenuItem).options(joinedload(MenuItem.page), joinedload(MenuItem.parent))
        if location:
            query = query.filter(MenuItem.location == location)
        return query.order_by(
            MenuItem.location.asc(),
            MenuItem.parent_id.asc(),
            MenuItem.display_order.asc(),
            MenuItem.id.asc(),
        ).all()

    def get_item_by_id(self, db: Session, item_id: int) -> Optional[MenuItem]:
        return db.query(MenuItem).filter(MenuItem.id == item_id).first()

    def create_menu_item(self, db: Session, data: Dict[str, Any]) -> MenuItem:
        title = data.get("title", "").strip()
        if not title:
            raise ValueError("Menu item title is required.")

        page_id = data.get("page_id")
        if page_id and page_id != "" and page_id != "0":
            page_id = int(page_id)
        else:
            page_id = None

        url = data.get("url", "").strip()
        if not url and not page_id:
            url = "#"

        parent_id = data.get("parent_id")
        if parent_id and parent_id != "" and parent_id != "0":
            parent_id = int(parent_id)
        else:
            parent_id = None

        location = data.get("location", MenuLocation.HEADER.value)
        display_order = int(data.get("display_order", 0))
        is_enabled = bool(data.get("is_enabled", True))
        target = data.get("target", "_self")

        item = MenuItem(
            title=title,
            url=url,
            page_id=page_id,
            parent_id=parent_id,
            location=location,
            display_order=display_order,
            is_enabled=is_enabled,
            target=target,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        logger.info(f"Created MenuItem id={item.id} title='{item.title}'")
        return item

    def update_menu_item(
        self, db: Session, item_id: int, data: Dict[str, Any]
    ) -> MenuItem:
        item = self.get_item_by_id(db, item_id)
        if not item:
            raise ValueError("Menu item not found.")

        title = data.get("title", item.title).strip()
        if not title:
            raise ValueError("Menu item title is required.")

        page_id = data.get("page_id")
        if page_id is not None:
            if page_id != "" and page_id != "0":
                item.page_id = int(page_id)
            else:
                item.page_id = None

        if "url" in data:
            item.url = data["url"].strip() or "#"

        if "parent_id" in data:
            parent_id = data["parent_id"]
            if parent_id and parent_id != "" and parent_id != "0":
                pid = int(parent_id)
                if pid == item_id:
                    raise ValueError("A menu item cannot be its own parent.")
                item.parent_id = pid
            else:
                item.parent_id = None

        if "location" in data:
            item.location = data["location"]
        if "display_order" in data:
            item.display_order = int(data["display_order"])
        if "is_enabled" in data:
            item.is_enabled = bool(data["is_enabled"])
        if "target" in data:
            item.target = data["target"]

        item.title = title
        db.commit()
        db.refresh(item)
        logger.info(f"Updated MenuItem id={item.id} title='{item.title}'")
        return item

    def delete_menu_item(self, db: Session, item_id: int) -> bool:
        item = self.get_item_by_id(db, item_id)
        if not item:
            return False
        db.delete(item)
        db.commit()
        logger.info(f"Deleted MenuItem id={item_id}")
        return True

    def reorder_items(self, db: Session, ordered_ids: List[int]) -> bool:
        for idx, item_id in enumerate(ordered_ids):
            db.query(MenuItem).filter(MenuItem.id == item_id).update(
                {"display_order": idx + 1}
            )
        db.commit()
        return True

    def seed_default_menus(self, db: Session) -> None:
        """Seeds standard navigation items including the dynamic About Us menu."""
        if db.query(MenuItem).count() > 0:
            return

        header_items = [
            {"title": "Home", "url": "/", "order": 1},
            {"title": "About Us", "url": "/about-us", "order": 2, "children": [
                {"title": "Company Profile", "url": "/about-us/company-profile", "order": 1},
                {"title": "Vision & Mission", "url": "/about-us/vision-mission", "order": 2},
                {"title": "Quality Policy", "url": "/about-us/quality-policy", "order": 3},
                {"title": "Infrastructure", "url": "/infrastructure", "order": 4},
                {"title": "Certifications", "url": "/quality/certifications", "order": 5},
                {"title": "Our Capabilities", "url": "/capabilities", "order": 6},
            ]},
            {"title": "Capabilities", "url": "/capabilities", "order": 3},
            {"title": "Products", "url": "/products", "order": 4},
            {"title": "Industries", "url": "/industries", "order": 5},
            {"title": "Case Studies", "url": "/case-studies", "order": 6},
            {"title": "Contact", "url": "/contact", "order": 7},
        ]

        for item_data in header_items:
            parent_item = MenuItem(
                title=item_data["title"],
                url=item_data["url"],
                location=MenuLocation.HEADER.value,
                display_order=item_data["order"],
                is_enabled=True,
                target="_self",
            )
            db.add(parent_item)
            db.flush()

            if "children" in item_data:
                for child_data in item_data["children"]:
                    child_item = MenuItem(
                        title=child_data["title"],
                        url=child_data["url"],
                        parent_id=parent_item.id,
                        location=MenuLocation.HEADER.value,
                        display_order=child_data["order"],
                        is_enabled=True,
                        target="_self",
                    )
                    db.add(child_item)

        db.commit()
        logger.info("Default navigation menus successfully seeded.")


menu_service = MenuService()
