from fastapi import APIRouter, status


router = APIRouter(prefix='/v1/health', tags=['Health'])

@router.get('/', status_code=status.HTTP_418_IM_A_TEAPOT)
async def health():
    pass
