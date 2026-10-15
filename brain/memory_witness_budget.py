"""Linux-only limits for explicitly approved finite fake-data child workers."""
import os
import sys

ADDRESS_SPACE_BYTES = 256 * 1024 * 1024
FILE_BYTES = 8 * 1024 * 1024
OPEN_FILES = 64
CPU_SECONDS = 10
LIMITS = (('RLIMIT_CORE',0),('RLIMIT_AS',ADDRESS_SPACE_BYTES),('RLIMIT_NOFILE',OPEN_FILES),
          ('RLIMIT_FSIZE',FILE_BYTES),('RLIMIT_CPU',CPU_SECONDS))


def apply_synthetic_budget(*,synthetic_only=False,approved=False):
    """Irreversible calling-process hard ceilings; use only in owned lab children."""
    if synthetic_only is not True or approved is not True:
        raise PermissionError('Explicit approved fake-data child budget required.')
    if sys.platform!='linux':raise OSError('Linux process limits required; never silently run unbounded.')
    import resource
    plan=[]
    for name,ceiling in LIMITS:
        kind=getattr(resource,name);soft,hard=resource.getrlimit(kind)
        hard=ceiling if hard==resource.RLIM_INFINITY else min(hard,ceiling)
        soft=hard if soft==resource.RLIM_INFINITY else min(soft,hard)
        if name=='RLIMIT_AS':
            with open('/proc/self/statm') as status:mapped=int(status.read().split()[0])*os.sysconf('SC_PAGE_SIZE')
            if mapped>soft:raise OSError('Worker already exceeds its address-space budget; refuse startup.')
        plan.append((name,kind,(soft,hard)))
    result={}
    for name,kind,limits in plan:
        resource.setrlimit(kind,limits)
        actual=resource.getrlimit(kind)
        if actual!=limits:raise OSError('Process budget was not applied; worker must exit.')
        result[name]=actual
    return result
