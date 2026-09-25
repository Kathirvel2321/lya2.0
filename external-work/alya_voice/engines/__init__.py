"""Engine registry. Imports are lazy so a missing optional dependency is a
    reported 'unavailable' engine, never an import crash."""
from .base import Chunk, Engine, EngineError

_LAZY = {
    'neural_edge': ('.neural_edge', 'NeuralEdgeEngine'),
    'offline_piper': ('.offline_piper', 'PiperEngine'),
    'offline_sapi': ('.offline_sapi', 'SapiEngine'),
    'cloud_edge': ('.cloud_edge', 'EdgeEngine'),
}

ENGINE_NAMES = tuple(_LAZY)


def engine_class(name):
    if name not in _LAZY:
        raise KeyError('unknown engine %r; known: %s' % (name, ', '.join(ENGINE_NAMES)))
    import importlib
    module_name, class_name = _LAZY[name]
    module = importlib.import_module(module_name, __package__)
    return getattr(module, class_name)


def build(name, persona, **kwargs):
    return engine_class(name)(persona, **kwargs)


__all__ = ['Chunk', 'Engine', 'EngineError', 'ENGINE_NAMES', 'build', 'engine_class']
