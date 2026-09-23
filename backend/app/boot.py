"""Install offline protection before loading model providers."""

from app.speech import guard
from app.speech.cuda import preload_cuda_libs

guard.install()
preload_cuda_libs()
