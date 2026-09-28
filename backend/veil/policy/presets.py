from __future__ import annotations

from ..models import Policy, PrivacyAction


PRESETS: dict[str, Policy] = {
    "public": Policy(
        id="public",
        name="Public Presentation",
        description="Aggressive masking for demos, classrooms, livestreams and public presentations.",
        actions={
            "AUTH_CREDENTIAL": PrivacyAction.BLOCK,
            "IDENTITY": PrivacyAction.BLOCK,
            "CONTACT": PrivacyAction.BLOCK,
            "FINANCIAL": PrivacyAction.BLOCK,
            "CONFIDENTIAL_WORK": PrivacyAction.BLOCK,
            "PRIVATE_COMMUNICATION": PrivacyAction.BLOCK,
            "HEALTH": PrivacyAction.BLOCK,
            "LOCATION": PrivacyAction.BLOCK,
            "QR_CODE": PrivacyAction.BLOCK,
            "FACE": PrivacyAction.BLUR,
            "CUSTOM": PrivacyAction.BLOCK,
            "UNKNOWN": PrivacyAction.BLOCK,
        },
        mask_faces=True,
        mask_qr=True,
    ),
    "external": Policy(
        id="external",
        name="External Meeting",
        description="Protect credentials, personal data and confidential work while collaborating outside your organization.",
        actions={
            "AUTH_CREDENTIAL": PrivacyAction.BLOCK,
            "IDENTITY": PrivacyAction.BLOCK,
            "CONTACT": PrivacyAction.BLOCK,
            "FINANCIAL": PrivacyAction.BLOCK,
            "CONFIDENTIAL_WORK": PrivacyAction.BLOCK,
            "PRIVATE_COMMUNICATION": PrivacyAction.BLOCK,
            "HEALTH": PrivacyAction.BLOCK,
            "LOCATION": PrivacyAction.BLOCK,
            "QR_CODE": PrivacyAction.BLOCK,
            "FACE": PrivacyAction.ALLOW,
            "CUSTOM": PrivacyAction.BLOCK,
            "UNKNOWN": PrivacyAction.BLOCK,
        },
        mask_faces=False,
        mask_qr=True,
    ),
    "internal": Policy(
        id="internal",
        name="Internal Meeting",
        description="Lighter masking for trusted internal collaboration.",
        actions={
            "AUTH_CREDENTIAL": PrivacyAction.BLOCK,
            "IDENTITY": PrivacyAction.BLOCK,
            "CONTACT": PrivacyAction.ALLOW,
            "FINANCIAL": PrivacyAction.BLOCK,
            "CONFIDENTIAL_WORK": PrivacyAction.ALLOW,
            "PRIVATE_COMMUNICATION": PrivacyAction.WARN,
            "HEALTH": PrivacyAction.BLOCK,
            "LOCATION": PrivacyAction.WARN,
            "QR_CODE": PrivacyAction.WARN,
            "FACE": PrivacyAction.ALLOW,
            "CUSTOM": PrivacyAction.BLOCK,
            "UNKNOWN": PrivacyAction.WARN,
        },
        mask_faces=False,
        mask_qr=False,
    ),
    "strict": Policy(
        id="strict",
        name="Strict Privacy",
        description="Maximum protection. Mask every recognized privacy class, faces and QR codes.",
        actions={
            "AUTH_CREDENTIAL": PrivacyAction.BLOCK,
            "IDENTITY": PrivacyAction.BLOCK,
            "CONTACT": PrivacyAction.BLOCK,
            "FINANCIAL": PrivacyAction.BLOCK,
            "CONFIDENTIAL_WORK": PrivacyAction.BLOCK,
            "PRIVATE_COMMUNICATION": PrivacyAction.BLOCK,
            "HEALTH": PrivacyAction.BLOCK,
            "LOCATION": PrivacyAction.BLOCK,
            "QR_CODE": PrivacyAction.BLOCK,
            "FACE": PrivacyAction.BLUR,
            "CUSTOM": PrivacyAction.BLOCK,
            "UNKNOWN": PrivacyAction.BLOCK,
        },
        mask_faces=True,
        mask_qr=True,
    ),
}


def get_policy(policy_id: str) -> Policy:
    return PRESETS.get(policy_id, PRESETS["external"]).model_copy(deep=True)
