from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.user import User
from app.models.product import (
    Product,
    ProductCategory,
    ProductSpecification,
    ProductImage,
    MeasurementUnit,
)
from app.models.capability import Capability
from app.models.industry import Industry
from app.models.material import Material
from app.models.infrastructure import Equipment
from app.admin.dependencies import get_current_admin
from app.core.templates import templates
from app.utils.slug import get_unique_slug, slugify
from app.services.upload_service import upload_service
from app.core.logging import logger


router = APIRouter(tags=["Admin - Products"])


# ==============================================================================
# PRODUCTS CRUD
# ==============================================================================

@router.get("/products", response_class=HTMLResponse)
async def list_products(
    request: Request,
    category_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if status_filter:
        query = query.filter(Product.status == status_filter)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))

    products = query.order_by(Product.display_order.asc(), Product.id.desc()).all()
    categories = db.query(ProductCategory).order_by(ProductCategory.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/products/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "products": products,
            "categories": categories,
            "category_id": category_id,
            "status_filter": status_filter,
            "q": q,
            "active_page": "products",
            "active_subpage": "products_list",
        },
    )


@router.get("/products/create", response_class=HTMLResponse)
async def create_product_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    categories = db.query(ProductCategory).order_by(ProductCategory.name.asc()).all()
    capabilities = db.query(Capability).order_by(Capability.title.asc()).all()
    industries = db.query(Industry).order_by(Industry.name.asc()).all()
    materials = db.query(Material).order_by(Material.name.asc()).all()
    equipment = db.query(Equipment).order_by(Equipment.name.asc()).all()
    units = db.query(MeasurementUnit).filter(MeasurementUnit.is_active == True).order_by(MeasurementUnit.unit_type, MeasurementUnit.display_order).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/products/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "product": None,
            "categories": categories,
            "capabilities": capabilities,
            "industries": industries,
            "materials": materials,
            "equipment": equipment,
            "units": units,
            "active_page": "products",
            "active_subpage": "products_list",
        },
    )


@router.post("/products/create", response_class=HTMLResponse)
async def create_product_post(
    request: Request,
    name: str = Form(...),
    slug: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    short_description: Optional[str] = Form(None),
    detailed_description: Optional[str] = Form(None),
    applications: Optional[str] = Form(None),
    material: Optional[str] = Form(None),
    weight_range: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    manufacturing_process: Optional[str] = Form(None),
    forging_capacity: Optional[str] = Form(None),
    heat_treatment: Optional[str] = Form(None),
    machining: Optional[str] = Form(None),
    surface_finish: Optional[str] = Form(None),
    testing: Optional[str] = Form(None),
    technical_specifications: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    status: str = Form("published"),
    display_order: int = Form(0),
    capability_ids: List[int] = Form([]),
    industry_ids: List[int] = Form([]),
    material_ids: List[int] = Form([]),
    equipment_ids: List[int] = Form([]),
    featured_image_file: Optional[UploadFile] = File(None),
    download_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_slug = get_unique_slug(db, Product, slug or name)

    featured_image_url = None
    if featured_image_file and featured_image_file.filename:
        try:
            featured_image_url, _ = upload_service.save_upload(featured_image_file, subfolder="products", is_image=True)
        except Exception as exc:
            logger.warning(f"Featured image upload failed: {exc}")

    download_url = None
    if download_file and download_file.filename:
        try:
            download_url, _ = upload_service.save_upload(download_file, subfolder="brochures", is_image=False)
        except Exception as exc:
            logger.warning(f"Brochure download upload failed: {exc}")

    product = Product(
        name=name.strip(),
        slug=clean_slug,
        category_id=category_id if category_id and category_id > 0 else None,
        short_description=short_description,
        detailed_description=detailed_description,
        applications=applications,
        material=material,
        weight_range=weight_range,
        dimensions=dimensions,
        manufacturing_process=manufacturing_process,
        forging_capacity=forging_capacity,
        heat_treatment=heat_treatment,
        machining=machining,
        surface_finish=surface_finish,
        testing=testing,
        technical_specifications=technical_specifications,
        featured_image=featured_image_url,
        downloads=download_url,
        meta_title=meta_title or name,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        status=status,
        display_order=display_order,
    )

    if capability_ids:
        product.capabilities = db.query(Capability).filter(Capability.id.in_(capability_ids)).all()
    if industry_ids:
        product.industries = db.query(Industry).filter(Industry.id.in_(industry_ids)).all()
    if material_ids:
        product.materials = db.query(Material).filter(Material.id.in_(material_ids)).all()
    if equipment_ids:
        product.equipment = db.query(Equipment).filter(Equipment.id.in_(equipment_ids)).all()

    db.add(product)
    db.commit()
    db.refresh(product)

    return RedirectResponse(url=f"/admin/products/{product.id}/edit?msg=created", status_code=status.HTTP_302_FOUND)


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
async def edit_product_form(
    product_id: int,
    request: Request,
    msg: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    categories = db.query(ProductCategory).order_by(ProductCategory.name.asc()).all()
    capabilities = db.query(Capability).order_by(Capability.title.asc()).all()
    industries = db.query(Industry).order_by(Industry.name.asc()).all()
    materials = db.query(Material).order_by(Material.name.asc()).all()
    equipment = db.query(Equipment).order_by(Equipment.name.asc()).all()
    units = db.query(MeasurementUnit).filter(MeasurementUnit.is_active == True).order_by(MeasurementUnit.unit_type, MeasurementUnit.display_order).all()
    all_products = db.query(Product).filter(Product.id != product_id).order_by(Product.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/products/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "product": product,
            "categories": categories,
            "capabilities": capabilities,
            "industries": industries,
            "materials": materials,
            "equipment": equipment,
            "units": units,
            "all_products": all_products,
            "msg": msg,
            "active_page": "products",
            "active_subpage": "products_list",
        },
    )


@router.post("/products/{product_id}/edit", response_class=HTMLResponse)
async def edit_product_post(
    product_id: int,
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    category_id: Optional[int] = Form(None),
    short_description: Optional[str] = Form(None),
    detailed_description: Optional[str] = Form(None),
    applications: Optional[str] = Form(None),
    material: Optional[str] = Form(None),
    weight_range: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    manufacturing_process: Optional[str] = Form(None),
    forging_capacity: Optional[str] = Form(None),
    heat_treatment: Optional[str] = Form(None),
    machining: Optional[str] = Form(None),
    surface_finish: Optional[str] = Form(None),
    testing: Optional[str] = Form(None),
    technical_specifications: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    status: str = Form("published"),
    display_order: int = Form(0),
    capability_ids: List[int] = Form([]),
    industry_ids: List[int] = Form([]),
    material_ids: List[int] = Form([]),
    equipment_ids: List[int] = Form([]),
    related_product_ids: List[int] = Form([]),
    featured_image_file: Optional[UploadFile] = File(None),
    download_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    clean_slug = get_unique_slug(db, Product, slug or name, current_id=product_id)

    if featured_image_file and featured_image_file.filename:
        try:
            img_url, _ = upload_service.save_upload(featured_image_file, subfolder="products", is_image=True)
            product.featured_image = img_url
        except Exception as exc:
            logger.warning(f"Featured image upload failed: {exc}")

    if download_file and download_file.filename:
        try:
            doc_url, _ = upload_service.save_upload(download_file, subfolder="brochures", is_image=False)
            product.downloads = doc_url
        except Exception as exc:
            logger.warning(f"Brochure download upload failed: {exc}")

    product.name = name.strip()
    product.slug = clean_slug
    product.category_id = category_id if category_id and category_id > 0 else None
    product.short_description = short_description
    product.detailed_description = detailed_description
    product.applications = applications
    product.material = material
    product.weight_range = weight_range
    product.dimensions = dimensions
    product.manufacturing_process = manufacturing_process
    product.forging_capacity = forging_capacity
    product.heat_treatment = heat_treatment
    product.machining = machining
    product.surface_finish = surface_finish
    product.testing = testing
    product.technical_specifications = technical_specifications
    product.meta_title = meta_title or name
    product.meta_description = meta_description
    product.meta_keywords = meta_keywords
    product.status = status
    product.display_order = display_order

    product.capabilities = db.query(Capability).filter(Capability.id.in_(capability_ids)).all() if capability_ids else []
    product.industries = db.query(Industry).filter(Industry.id.in_(industry_ids)).all() if industry_ids else []
    product.materials = db.query(Material).filter(Material.id.in_(material_ids)).all() if material_ids else []
    product.equipment = db.query(Equipment).filter(Equipment.id.in_(equipment_ids)).all() if equipment_ids else []
    product.related_products = db.query(Product).filter(Product.id.in_(related_product_ids)).all() if related_product_ids else []

    db.commit()
    return RedirectResponse(url=f"/admin/products/{product.id}/edit?msg=updated", status_code=status.HTTP_302_FOUND)


@router.post("/products/{product_id}/delete")
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse(url="/admin/products?msg=deleted", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# PRODUCT SPECIFICATIONS & IMAGES
# ==============================================================================

@router.post("/products/{product_id}/specifications/add")
async def add_product_specification(
    product_id: int,
    name: str = Form(...),
    value: str = Form(...),
    unit: Optional[str] = Form(""),
    display_order: int = Form(0),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    spec = ProductSpecification(
        product_id=product_id,
        name=name.strip(),
        value=value.strip(),
        unit=unit.strip() if unit else None,
        display_order=display_order,
    )
    db.add(spec)
    db.commit()
    return RedirectResponse(url=f"/admin/products/{product_id}/edit?msg=spec_added", status_code=status.HTTP_302_FOUND)


@router.post("/products/{product_id}/specifications/{spec_id}/delete")
async def delete_product_specification(
    product_id: int,
    spec_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    spec = db.query(ProductSpecification).filter(
        ProductSpecification.id == spec_id,
        ProductSpecification.product_id == product_id,
    ).first()
    if spec:
        db.delete(spec)
        db.commit()
    return RedirectResponse(url=f"/admin/products/{product_id}/edit?msg=spec_deleted", status_code=status.HTTP_302_FOUND)


@router.post("/products/{product_id}/images/add")
async def add_product_image(
    product_id: int,
    image_file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    display_order: int = Form(0),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        url, _ = upload_service.save_upload(image_file, subfolder="products", is_image=True)
        img = ProductImage(
            product_id=product_id,
            image_url=url,
            alt_text=alt_text or product.name,
            caption=caption,
            is_primary=is_primary,
            display_order=display_order,
        )
        db.add(img)
        db.commit()
    except Exception as exc:
        logger.warning(f"Product image gallery upload failed: {exc}")

    return RedirectResponse(url=f"/admin/products/{product_id}/edit?msg=image_added", status_code=status.HTTP_302_FOUND)


@router.post("/products/{product_id}/images/{image_id}/delete")
async def delete_product_image(
    product_id: int,
    image_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    img = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
    ).first()
    if img:
        db.delete(img)
        db.commit()
    return RedirectResponse(url=f"/admin/products/{product_id}/edit?msg=image_deleted", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# PRODUCT CATEGORIES CRUD
# ==============================================================================

@router.get("/categories", response_class=HTMLResponse)
@router.get("/products/categories", response_class=HTMLResponse)
async def list_categories(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    categories = db.query(ProductCategory).order_by(ProductCategory.display_order.asc(), ProductCategory.name.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/categories/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "categories": categories,
            "active_page": "products",
            "active_subpage": "categories",
        },
    )


@router.get("/categories/create", response_class=HTMLResponse)
@router.get("/products/categories/create", response_class=HTMLResponse)
async def create_category_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/categories/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "category": None,
            "active_page": "products",
            "active_subpage": "categories",
        },
    )


@router.post("/categories/create")
@router.post("/products/categories/create")
async def create_category_post(
    name: str = Form(...),
    slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_slug = get_unique_slug(db, ProductCategory, slug or name)
    image_url = None
    if image_file and image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(image_file, subfolder="categories", is_image=True)
        except Exception as exc:
            logger.warning(f"Category image upload failed: {exc}")

    cat = ProductCategory(
        name=name.strip(),
        slug=clean_slug,
        description=description,
        display_order=display_order,
        is_active=is_active,
        image=image_url,
        meta_title=meta_title or name,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
    )
    db.add(cat)
    db.commit()
    return RedirectResponse(url="/admin/categories?msg=created", status_code=status.HTTP_302_FOUND)


@router.get("/categories/{cat_id}/edit", response_class=HTMLResponse)
async def edit_category_form(
    cat_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(ProductCategory).filter(ProductCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/categories/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "category": cat,
            "active_page": "products",
            "active_subpage": "categories",
        },
    )


@router.post("/categories/{cat_id}/edit")
async def edit_category_post(
    cat_id: int,
    name: str = Form(...),
    slug: str = Form(...),
    description: Optional[str] = Form(None),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(ProductCategory).filter(ProductCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    cat.name = name.strip()
    cat.slug = get_unique_slug(db, ProductCategory, slug or name, current_id=cat_id)
    cat.description = description
    cat.display_order = display_order
    cat.is_active = is_active
    cat.meta_title = meta_title or name
    cat.meta_description = meta_description
    cat.meta_keywords = meta_keywords

    if image_file and image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(image_file, subfolder="categories", is_image=True)
            cat.image = image_url
        except Exception as exc:
            logger.warning(f"Category image upload failed: {exc}")

    db.commit()
    return RedirectResponse(url="/admin/categories?msg=updated", status_code=status.HTTP_302_FOUND)


@router.post("/categories/{cat_id}/delete")
async def delete_category(
    cat_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(ProductCategory).filter(ProductCategory.id == cat_id).first()
    if cat:
        db.delete(cat)
        db.commit()
    return RedirectResponse(url="/admin/categories?msg=deleted", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# SPECIFICATIONS & MEASUREMENT UNITS
# ==============================================================================

@router.get("/specifications", response_class=HTMLResponse)
@router.get("/products/specifications", response_class=HTMLResponse)
@router.get("/products/units", response_class=HTMLResponse)
async def list_specifications_overview(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    units = db.query(MeasurementUnit).order_by(MeasurementUnit.unit_type.asc(), MeasurementUnit.display_order.asc()).all()
    specs = db.query(ProductSpecification.name).distinct().all()
    spec_names = [s[0] for s in specs]

    return templates.TemplateResponse(
        request=request,
        name="admin/units/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "units": units,
            "spec_names": spec_names,
            "active_page": "products",
            "active_subpage": "specifications",
        },
    )


@router.get("/units/create", response_class=HTMLResponse)
@router.get("/products/units/create", response_class=HTMLResponse)
async def create_unit_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/units/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "unit": None,
            "active_page": "products",
            "active_subpage": "specifications",
        },
    )


@router.post("/units/create")
@router.post("/products/units/create")
async def create_unit_post(
    name: str = Form(...),
    symbol: str = Form(...),
    unit_type: str = Form(...),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    unit = MeasurementUnit(
        name=name.strip(),
        symbol=symbol.strip(),
        unit_type=unit_type.strip().lower(),
        display_order=display_order,
        is_active=is_active,
    )
    db.add(unit)
    db.commit()
    return RedirectResponse(url="/admin/specifications?msg=unit_created", status_code=status.HTTP_302_FOUND)


@router.get("/units/{unit_id}/edit", response_class=HTMLResponse)
async def edit_unit_form(
    unit_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    unit = db.query(MeasurementUnit).filter(MeasurementUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/units/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "unit": unit,
            "active_page": "products",
            "active_subpage": "specifications",
        },
    )


@router.post("/units/{unit_id}/edit")
async def edit_unit_post(
    unit_id: int,
    name: str = Form(...),
    symbol: str = Form(...),
    unit_type: str = Form(...),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    unit = db.query(MeasurementUnit).filter(MeasurementUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    unit.name = name.strip()
    unit.symbol = symbol.strip()
    unit.unit_type = unit_type.strip().lower()
    unit.display_order = display_order
    unit.is_active = is_active
    db.commit()
    return RedirectResponse(url="/admin/specifications?msg=unit_updated", status_code=status.HTTP_302_FOUND)


@router.post("/units/{unit_id}/delete")
async def delete_unit(
    unit_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    unit = db.query(MeasurementUnit).filter(MeasurementUnit.id == unit_id).first()
    if unit:
        db.delete(unit)
        db.commit()
    return RedirectResponse(url="/admin/specifications?msg=unit_deleted", status_code=status.HTTP_302_FOUND)
