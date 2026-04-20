"""
Stripe Webhook Handler.
Processes payment events and updates user credits/subscriptions.
"""

import os
import stripe
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from app.models.db import User, CreditTransaction
from app.models.database import get_db_context

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Credit packs mapping
CREDIT_PACKS = {
    "price_starter_10":  10,   # $5  → 10 credits
    "price_creator_50":  50,   # $20 → 50 credits
    "price_studio_200": 200,   # $69 → 200 credits
}

# Subscription tier credit allocation (monthly)
SUBSCRIPTION_CREDITS = {
    "price_pro_monthly": {"tier": "pro", "credits": 100},
    "price_enterprise_monthly": {"tier": "enterprise", "credits": 500},
}


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (checkout, subscription, refunds)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event["type"]
    data = event["data"]["object"]
    
    # ── Checkout completed (one-time credit purchase) ──
    if event_type == "checkout.session.completed":
        _handle_checkout(data)
    
    # ── Invoice paid (subscription renewal) ──
    elif event_type == "invoice.paid":
        _handle_subscription_payment(data)
    
    # ── Subscription cancelled ──
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_cancelled(data)
    
    # ── Charge refunded ──
    elif event_type == "charge.refunded":
        _handle_refund(data)
    
    return {"status": "ok"}


def _handle_checkout(session):
    """Process completed checkout — add credits to user."""
    customer_id = session.get("customer")
    if not customer_id:
        return
    
    with get_db_context() as db:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if not user:
            return
        
        # Determine credits from line items
        line_items = stripe.checkout.Session.list_line_items(session["id"])
        for item in line_items.get("data", []):
            price_id = item.get("price", {}).get("id", "")
            credits = CREDIT_PACKS.get(price_id, 0)
            if credits > 0:
                user.add_credits(credits)
                db.add(CreditTransaction(
                    user_id=user.id,
                    amount=credits,
                    type="purchase",
                    stripe_payment_id=session.get("payment_intent"),
                ))


def _handle_subscription_payment(invoice):
    """Process subscription payment — add monthly credits."""
    customer_id = invoice.get("customer")
    if not customer_id:
        return
    
    with get_db_context() as db:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if not user:
            return
        
        for line in invoice.get("lines", {}).get("data", []):
            price_id = line.get("price", {}).get("id", "")
            sub_info = SUBSCRIPTION_CREDITS.get(price_id)
            if sub_info:
                user.subscription_tier = sub_info["tier"]
                user.add_credits(sub_info["credits"])
                db.add(CreditTransaction(
                    user_id=user.id,
                    amount=sub_info["credits"],
                    type="purchase",
                    stripe_payment_id=invoice.get("payment_intent"),
                ))


def _handle_subscription_cancelled(subscription):
    """Downgrade user on cancellation."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return
    
    with get_db_context() as db:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_tier = "free"


def _handle_refund(charge):
    """Handle charge refund — deduct credits if possible."""
    customer_id = charge.get("customer")
    if not customer_id:
        return
    
    with get_db_context() as db:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            # Find original transaction
            txn = (
                db.query(CreditTransaction)
                .filter(CreditTransaction.stripe_payment_id == charge.get("payment_intent"))
                .first()
            )
            if txn and txn.amount > 0:
                refund_amount = min(txn.amount, user.credits)
                user.credits -= refund_amount
                db.add(CreditTransaction(
                    user_id=user.id,
                    amount=-refund_amount,
                    type="refund",
                    stripe_payment_id=charge.get("id"),
                ))
