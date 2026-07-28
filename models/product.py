from datetime import datetime
from typing import Optional
import re

from pydantic import field_validator, ValidationInfo
from sqlmodel import SQLModel, Field


# ============================================================
# CATEGORY MODELS
# ============================================================

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(
        index=True,
        unique=True,
        min_length=2,
        max_length=100
    )


class CategoryCreate(SQLModel):
    name: str


# ============================================================
# PRODUCT MODEL
# ============================================================

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(index=True)

    description: str

    brand: str = Field(index=True)

    category: str = Field(index=True)

    price: float = Field(gt=0)

    stock: int = Field(ge=0)

    warranty_months: int = Field(ge=0)

    sku: str = Field(index=True, unique=True)

    supplier_id: Optional[int] = Field(
        default=None,
        foreign_key="supplier.id"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )


# ============================================================
# PRODUCT CREATE
# ============================================================

class ProductCreate(SQLModel):
    name: str = Field(min_length=2, max_length=100)

    description: str = Field(
        min_length=10,
        max_length=500
    )

    brand: str

    category: str

    price: float = Field(gt=0)

    stock: int = Field(ge=0)

    warranty_months: int = Field(ge=0)

    sku: str

    supplier_id: Optional[int] = None

    # --------------------------------------------------------
    # NAME VALIDATION
    # --------------------------------------------------------

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v[0].isupper():
            raise ValueError(
                "Name must start with a capital letter"
            )

        if re.search(r"[^a-zA-Z0-9\s-]", v):
            raise ValueError(
                "Name cannot contain special characters"
            )

        if len(v.split()) < 1:
            raise ValueError(
                "Name must contain at least one word"
            )

        return v

    # --------------------------------------------------------
    # BRAND VALIDATION
    # --------------------------------------------------------

    @field_validator("brand")
    @classmethod
    def validate_brand(cls, v):

        brands = {
            "hp": "HP",
            "dell": "Dell",
            "lenovo": "Lenovo",
            "apple": "Apple",
            "samsung": "Samsung",
            "intel": "Intel",
            "amd": "AMD",
            "corsair": "Corsair",
            "logitech": "Logitech",
            "other": "Other",
        }

        key = v.strip().lower()

        if key not in brands:
            raise ValueError("Invalid brand")

        return brands[key]

    # --------------------------------------------------------
    # CATEGORY VALIDATION
    # --------------------------------------------------------

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):

        categories = {
            "laptops": "Laptops",
            "monitors": "Monitors",
            "storage": "Storage",
            "processors": "Processors",
            "memory": "Memory",
            "keyboards": "Keyboards",
            "mice": "Mice",
            "accessories": "Accessories",
        }

        key = v.strip().lower()

        if key not in categories:
            raise ValueError("Invalid category")

        return categories[key]

    # --------------------------------------------------------
    # PRICE VALIDATION
    # --------------------------------------------------------

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):

        if round(v, 2) != v:
            raise ValueError(
                "Price must have at most 2 decimal places"
            )

        if v < 100:
            raise ValueError(
                "Minimum price is KSh 100"
            )

        if v > 500000:
            raise ValueError(
                "Maximum price is KSh 500,000"
            )

        return round(v, 2)

    # --------------------------------------------------------
    # SKU VALIDATION
    # --------------------------------------------------------

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v):

        pattern = r"^[A-Z]{3,4}-[A-Z]{2,4}-[0-9]{4}$"

        if not re.match(pattern, v):
            raise ValueError(
                "SKU must follow CAT-BRAND-XXXX format"
            )

        allowed = {
            "LAP",
            "MON",
            "STO",
            "PRO",
            "MEM",
            "KEY",
            "MOU",
            "ACC",
        }

        prefix = v.split("-")[0]

        if prefix not in allowed:
            raise ValueError(
                "Invalid category code in SKU"
            )

        return v

    # --------------------------------------------------------
    # WARRANTY VALIDATION
    # --------------------------------------------------------

    @field_validator("warranty_months")
    @classmethod
    def validate_warranty(cls, v, info: ValidationInfo):

        if v < 0 or v > 36:
            raise ValueError(
                "Warranty must be between 0 and 36 months"
            )

        price = info.data.get("price")

        if price is not None and price > 50000 and v < 12:
            raise ValueError(
                "Products above KSh 50,000 require at least 12 months warranty"
            )

        return v
        
 # ============================================================
# PRODUCT UPDATE
# ============================================================

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    warranty_months: Optional[int] = None
    sku: Optional[str] = None
    supplier_id: Optional[int] = None


class StockAdjustment(SQLModel):
    product_id: int
    quantity_to_add: int = Field(gt=0)


# ============================================================
# SUPPLIER MODELS
# ============================================================

class Supplier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(
        index=True,
        unique=True,
        min_length=2,
        max_length=100
    )



    contact_person: str = Field(
        min_length=2,
        max_length=100
    )

    email: str = Field(
        index=True,
        unique=True
    )

    phone: str

    is_active: bool = Field(default=True)


class SupplierCreate(SQLModel):
    name: str = Field(
        min_length=2,
        max_length=100
    )

    contact_person: str = Field(
        min_length=2,
        max_length=100
    )

    email: str

    phone: str

    is_active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

        if not re.match(pattern, v):
            raise ValueError("Invalid email format")

        return v.lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        pattern = r"^(?:\+254|0)[17]\d{8}$"

        if not re.match(pattern, v):
            raise ValueError(
                "Phone number must be a valid Kenyan number"
            )

        return v       