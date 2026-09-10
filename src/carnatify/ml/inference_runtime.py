"""Runtime-only controls for small-query evaluation; never changes weights."""


def serial_forest_prediction(model):
    """Avoid per-tree thread startup and warning-filter races on tiny queries.

    The installed sklearn parallel wrapper resets Python 3.11's process-global
    warning filters in worker threads. Repeated threaded calls intermittently
    emitted a warning for every tree. Serial prediction avoids this path without
    suppressing diagnostics or modifying persisted model artifacts.
    """
    if hasattr(model,'n_jobs'):model.n_jobs=1
    for name in ('hist_','tdms_'):
        child=getattr(model,name,None)
        if child is not None:serial_forest_prediction(child)
    return model
