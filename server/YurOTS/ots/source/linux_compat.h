#ifndef YUROTS_LINUX_COMPAT_H
#define YUROTS_LINUX_COMPAT_H

#define _timeb timeb
#define _ftime  ftime

#define ltoa(v,b,r)    (sprintf((b), "%ld", (long)(v)), (b))
#define _ultoa(v,b,r)  (sprintf((b), "%lu", (unsigned long)(v)), (b))
#define _i64toa(v,b,r) (sprintf((b), "%lld", (long long)(v)), (b))
#define _ui64toa(v,b,r) (sprintf((b), "%llu", (unsigned long long)(v)), (b))

#endif
