from datetime import datetime
from typing import List, Optional
import logging

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session, select

from database.session import engine, get_session
from models.product import (
    Product,
    ProductCreate,
    ProductUpdate,
    Supplier,
    SupplierCreate,
    StockAdjustment,
)



SQLModel.metadata.create_all(engine)


app = FastAPI(
    title="TechVault Inventory API",
    version="1.0.0",
    description="Inventory Management API"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "status_code": exc.status_code,
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    errors = []

    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(i) for i in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "status_code": 422,
            "message": "Validation Error",
            "timestamp": datetime.utcnow().isoformat(),
            "errors": errors,
            "path": request.url.path,
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):

    logger.error(str(exc))

    return JSONResponse(
        status_code=409,
        content={
            "success": False,
            "status_code": 409,
            "message": "Duplicate SKU or database constraint violation",
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):

    logger.error(str(exc))

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "status_code": 500,
            "message": "Internal Server Error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )


@app.get("/")
def root():
    return {
        "message": "Welcome to TechVault Inventory API"
    }


@app.post("/suppliers", response_model=Supplier, status_code=201)
def create_supplier(
    supplier: SupplierCreate,
    session: Session = Depends(get_session),
):

    existing = session.exec(
        select(Supplier).where(Supplier.email == supplier.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Supplier email already exists"
        )

    db_supplier = Supplier(**supplier.model_dump())

    session.add(db_supplier)
    session.commit()
    session.refresh(db_supplier)

    return db_supplier


@app.get("/suppliers", response_model=List[Supplier])
def list_suppliers(
    session: Session = Depends(get_session),
):
    return session.exec(select(Supplier)).all()


@app.get("/suppliers/{supplier_id}", response_model=Supplier)
def get_supplier(
    supplier_id: int,
    session: Session = Depends(get_session),
):

    supplier = session.get(Supplier, supplier_id)

    if supplier is None:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found"
        )

    return supplier
    
   

@app.post("/products", response_model=Product, status_code=201)
def create_product(
    product: ProductCreate,
    session: Session = Depends(get_session),
):
    if product.supplier_id is not None:
        supplier = session.get(Supplier, product.supplier_id)

        if supplier is None:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found",
            )

    db_product = Product(**product.model_dump())

    session.add(db_product)
    session.commit()
    session.refresh(db_product)

    return db_product



@app.get("/products", response_model=List[Product])
def list_products(
    skip: int = 0,
    limit: int = 10,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    session: Session = Depends(get_session),
):

    query = select(Product)

    if brand:
        query = query.where(Product.brand == brand)

    if category:
        query = query.where(Product.category == category)

    return session.exec(
        query.offset(skip).limit(limit)
    ).all()

@app.get("/products/search", response_model=List[Product])
def search_products(
    q: str,
    session: Session = Depends(get_session),
):
    query = select(Product).where(
        Product.name.contains(q)
        | Product.description.contains(q)
        | Product.brand.contains(q)
        | Product.category.contains(q)
    )

    return session.exec(query).all()
    

@app.get("/products/{product_id}", response_model=Product)
def get_product(
    product_id: int,
    session: Session = Depends(get_session),
):

    product = session.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product



@app.patch("/products/{product_id}", response_model=Product)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    session: Session = Depends(get_session),
):

    product = session.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    update_data = product_update.model_dump(exclude_unset=True)

    if (
        "supplier_id" in update_data
        and update_data["supplier_id"] is not None
    ):
        supplier = session.get(Supplier, update_data["supplier_id"])

        if supplier is None:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found",
            )

    for key, value in update_data.items():
        setattr(product, key, value)

    product.updated_at = datetime.utcnow()

    session.add(product)
    session.commit()
    session.refresh(product)

    return product



@app.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    session: Session = Depends(get_session),
):

    product = session.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    session.delete(product)
    session.commit()

    return None
    
   

@app.patch("/products/bulk-update")
def bulk_update_price(
    category: str,
    discount_percent: float,
    session: Session = Depends(get_session),
):
    if discount_percent <= 0 or discount_percent >= 100:
        raise HTTPException(
            status_code=400,
            detail="Discount percentage must be between 0 and 100."
        )

    products = session.exec(
        select(Product).where(Product.category == category)
    ).all()

    if not products:
        raise HTTPException(
            status_code=404,
            detail="No products found in this category."
        )

    updated = 0

    for product in products:
        new_price = product.price * (1 - discount_percent / 100)

        if new_price < 100:
            continue

        product.price = round(new_price, 2)
        product.updated_at = datetime.utcnow()

        session.add(product)
        updated += 1

    session.commit()

    logger.info(
        f"{updated} products updated in category {category}"
    )

    return {
        "message": "Bulk update completed",
        "updated_products": updated,
        "category": category,
        "discount": discount_percent,
    }
    
   
@app.patch("/products/adjust-stock")
def adjust_stock(
    adjustments: List[StockAdjustment],
    session: Session = Depends(get_session),
):
    successful = []
    failed = []

    for adjustment in adjustments:

        product = session.get(Product, adjustment.product_id)

        if product is None:
            failed.append({
                "product_id": adjustment.product_id,
                "reason": "Product not found"
            })
            continue

        new_stock = product.stock + adjustment.quantity_to_add

        if new_stock > 5000:
            failed.append({
                "product_id": adjustment.product_id,
                "reason": "Stock cannot exceed 5000"
            })
            continue

        product.stock = new_stock
        product.updated_at = datetime.utcnow()

        session.add(product)

        successful.append({
            "product_id": product.id,
            "new_stock": product.stock
        })

    session.commit()

    logger.info(
        f"Adjusted stock for {len(successful)} products"
    )

    return {
        "successful_updates": successful,
        "failed_updates": failed
    }