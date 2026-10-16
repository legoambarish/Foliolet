"""No public receiver endpoint and no change to credential/provenance formats."""
from uuid import UUID
from django.views.decorators.http import require_POST
from .intake_views import private
from . import wallet_api as api
from .pdf_signatures import inspect_pdf
from .wallet_views import page


@require_POST
@private
def inspect(request, credential_id):
    identifier=str(UUID(credential_id))
    document=api.call('GET',f'/api/wallet/documents/{identifier}',request.session['sb_auth'])
    if document.get('intake',{}).get('format')!='pdf':
        raise api.WalletAPIError('Signature inspection currently supports PDF originals only.',400)
    original,_=api.call('GET',f'/api/wallet/documents/{identifier}/file',request.session['sb_auth'],binary=True)
    report=inspect_pdf(original)
    report['credentialId']=identifier
    report['credentialVersion']=document['version']
    return page(request,'signature_report',document=document,inspection=report)
