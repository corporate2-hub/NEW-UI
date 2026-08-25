def company_context(request):
    return {
        'company': getattr(request, 'company', None)
    }
