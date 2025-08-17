"""
Payments Feature Module

Provides Stripe integration for payment processing including
one-time payments, subscriptions, and webhook handling.
"""

from typing import List, Optional, Dict, Any
from app.services.feature_modules import BaseFeatureModule, FeatureModule, FeatureModuleFactory


class PaymentsFeatureModule(BaseFeatureModule):
    """Payments feature module implementation"""
    
    def get_dependencies(self) -> List[str]:
        return [
            "stripe==7.4.0",
            "pydantic[email]==2.5.0"
        ]
    
    def get_environment_vars(self) -> List[str]:
        return [
            "STRIPE_SECRET_KEY",
            "STRIPE_PUBLISHABLE_KEY", 
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_WEBHOOK_ENDPOINT"
        ]
    
    def generate_service_code(self) -> str:
        return '''"""
Payment Service

Handles Stripe payment processing, subscriptions, and webhooks.
"""

import stripe
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from app.core.config import settings

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentService:
    """Service for payment processing using Stripe"""
    
    def __init__(self):
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    async def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create Stripe payment intent"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,  # Amount in cents
                currency=currency,
                customer=customer_id,
                metadata=metadata or {},
                automatic_payment_methods={
                    'enabled': True,
                }
            )
            
            return {
                "client_secret": intent.client_secret,
                "id": intent.id,
                "amount": intent.amount,
                "currency": intent.currency,
                "status": intent.status
            }
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment intent creation failed: {str(e)}"
            )
    
    async def confirm_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """Confirm payment intent"""
        try:
            intent = stripe.PaymentIntent.confirm(payment_intent_id)
            return {
                "id": intent.id,
                "status": intent.status,
                "amount_received": intent.amount_received,
                "charges": [
                    {
                        "id": charge.id,
                        "amount": charge.amount,
                        "status": charge.status,
                        "receipt_url": charge.receipt_url
                    }
                    for charge in intent.charges.data
                ]
            }
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment confirmation failed: {str(e)}"
            )
    
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            
            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "created": customer.created
            }
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer creation failed: {str(e)}"
            )
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create subscription for customer"""
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                metadata=metadata or {},
                payment_behavior="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
                expand=["latest_invoice.payment_intent"]
            )
            
            return {
                "id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end
            }
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subscription creation failed: {str(e)}"
            )
    
    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel subscription"""
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            return {
                "id": subscription.id,
                "status": subscription.status,
                "canceled_at": subscription.canceled_at
            }
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subscription cancellation failed: {str(e)}"
            )
    
    async def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload"
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature"
            )
        
        # Handle different event types
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            await self._handle_payment_success(payment_intent)
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            await self._handle_payment_failure(payment_intent)
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            await self._handle_invoice_payment_success(invoice)
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            await self._handle_subscription_cancelled(subscription)
        
        return {"received": True}
    
    async def _handle_payment_success(self, payment_intent: Dict[str, Any]):
        """Handle successful payment"""
        # Implement your business logic here
        # e.g., update order status, send confirmation email
        pass
    
    async def _handle_payment_failure(self, payment_intent: Dict[str, Any]):
        """Handle failed payment"""
        # Implement your business logic here
        # e.g., notify customer, retry payment
        pass
    
    async def _handle_invoice_payment_success(self, invoice: Dict[str, Any]):
        """Handle successful invoice payment"""
        # Implement your business logic here
        # e.g., activate subscription, send receipt
        pass
    
    async def _handle_subscription_cancelled(self, subscription: Dict[str, Any]):
        """Handle cancelled subscription"""
        # Implement your business logic here
        # e.g., deactivate account, send confirmation
        pass

# Global payment service instance
payment_service = PaymentService()
'''
    
    def generate_router_code(self) -> str:
        return '''"""
Payments Router

Provides payment endpoints for processing payments and subscriptions.
"""

from fastapi import APIRouter, HTTPException, status, Request, Header
from typing import Optional
from app.services.payment_service import payment_service
from app.schemas.payments import (
    PaymentIntentRequest, PaymentIntentResponse,
    CustomerRequest, CustomerResponse,
    SubscriptionRequest, SubscriptionResponse
)

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/create-payment-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(request: PaymentIntentRequest):
    """Create payment intent for one-time payment"""
    payment_intent = await payment_service.create_payment_intent(
        amount=request.amount,
        currency=request.currency,
        customer_id=request.customer_id,
        metadata=request.metadata
    )
    return PaymentIntentResponse(**payment_intent)

@router.post("/confirm-payment/{payment_intent_id}")
async def confirm_payment(payment_intent_id: str):
    """Confirm payment intent"""
    result = await payment_service.confirm_payment_intent(payment_intent_id)
    return result

@router.post("/create-customer", response_model=CustomerResponse)
async def create_customer(request: CustomerRequest):
    """Create Stripe customer"""
    customer = await payment_service.create_customer(
        email=request.email,
        name=request.name,
        metadata=request.metadata
    )
    return CustomerResponse(**customer)

@router.post("/create-subscription", response_model=SubscriptionResponse)
async def create_subscription(request: SubscriptionRequest):
    """Create subscription for customer"""
    subscription = await payment_service.create_subscription(
        customer_id=request.customer_id,
        price_id=request.price_id,
        metadata=request.metadata
    )
    return SubscriptionResponse(**subscription)

@router.delete("/cancel-subscription/{subscription_id}")
async def cancel_subscription(subscription_id: str):
    """Cancel subscription"""
    result = await payment_service.cancel_subscription(subscription_id)
    return result

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="stripe-signature")
):
    """Handle Stripe webhooks"""
    payload = await request.body()
    result = await payment_service.handle_webhook(payload, stripe_signature)
    return result

@router.get("/payment-methods/{customer_id}")
async def get_payment_methods(customer_id: str):
    """Get customer payment methods"""
    # This would typically fetch from your database
    # or call Stripe API to get saved payment methods
    return {"payment_methods": []}
'''
    
    def generate_middleware_code(self) -> Optional[str]:
        return '''"""
Payment Middleware

Provides middleware for payment security and validation.
"""

from fastapi import Request, HTTPException, status
import hmac
import hashlib

class PaymentMiddleware:
    """Middleware for payment processing security"""
    
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
    
    async def __call__(self, request: Request, call_next):
        # Validate webhook signatures for payment endpoints
        if request.url.path == "/payments/webhook":
            stripe_signature = request.headers.get("stripe-signature")
            if not stripe_signature:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing Stripe signature header"
                )
        
        # Add security headers for payment pages
        response = await call_next(request)
        
        if request.url.path.startswith("/payments/"):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
'''
    
    def generate_schema_code(self) -> Optional[str]:
        return '''"""
Payment Schemas

Pydantic models for payment requests and responses.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from decimal import Decimal

class PaymentIntentRequest(BaseModel):
    """Payment intent creation request"""
    amount: int  # Amount in cents
    currency: str = "usd"
    customer_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

class PaymentIntentResponse(BaseModel):
    """Payment intent response"""
    client_secret: str
    id: str
    amount: int
    currency: str
    status: str

class CustomerRequest(BaseModel):
    """Customer creation request"""
    email: EmailStr
    name: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

class CustomerResponse(BaseModel):
    """Customer response"""
    id: str
    email: str
    name: Optional[str]
    created: int

class SubscriptionRequest(BaseModel):
    """Subscription creation request"""
    customer_id: str
    price_id: str
    metadata: Optional[Dict[str, str]] = None

class SubscriptionResponse(BaseModel):
    """Subscription response"""
    id: str
    client_secret: str
    status: str
    current_period_start: int
    current_period_end: int

class WebhookEvent(BaseModel):
    """Webhook event schema"""
    id: str
    type: str
    data: Dict[str, Any]
    created: int
'''
    
    def get_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Payment",
                "fields": [
                    {"name": "id", "type": "String", "constraints": ["primary_key"]},
                    {"name": "stripe_payment_intent_id", "type": "String", "constraints": ["unique"]},
                    {"name": "customer_id", "type": "String", "constraints": []},
                    {"name": "amount", "type": "Integer", "constraints": ["required"]},
                    {"name": "currency", "type": "String(3)", "constraints": ["required"]},
                    {"name": "status", "type": "String(50)", "constraints": ["required"]},
                    {"name": "metadata", "type": "JSON", "constraints": []},
                    {"name": "created_at", "type": "DateTime", "constraints": []},
                    {"name": "updated_at", "type": "DateTime", "constraints": []}
                ]
            },
            {
                "name": "Subscription",
                "fields": [
                    {"name": "id", "type": "String", "constraints": ["primary_key"]},
                    {"name": "stripe_subscription_id", "type": "String", "constraints": ["unique"]},
                    {"name": "customer_id", "type": "String", "constraints": ["required"]},
                    {"name": "price_id", "type": "String", "constraints": ["required"]},
                    {"name": "status", "type": "String(50)", "constraints": ["required"]},
                    {"name": "current_period_start", "type": "DateTime", "constraints": []},
                    {"name": "current_period_end", "type": "DateTime", "constraints": []},
                    {"name": "created_at", "type": "DateTime", "constraints": []},
                    {"name": "canceled_at", "type": "DateTime", "constraints": []}
                ]
            }
        ]
    
    def get_endpoints(self) -> List[Dict[str, Any]]:
        return [
            {"path": "/payments/create-payment-intent", "method": "POST", "description": "Create payment intent"},
            {"path": "/payments/confirm-payment/{payment_intent_id}", "method": "POST", "description": "Confirm payment"},
            {"path": "/payments/create-customer", "method": "POST", "description": "Create Stripe customer"},
            {"path": "/payments/create-subscription", "method": "POST", "description": "Create subscription"},
            {"path": "/payments/cancel-subscription/{subscription_id}", "method": "DELETE", "description": "Cancel subscription"},
            {"path": "/payments/webhook", "method": "POST", "description": "Stripe webhook handler"}
        ]


# Register the module
FeatureModuleFactory.register(FeatureModule.PAYMENTS, PaymentsFeatureModule)
