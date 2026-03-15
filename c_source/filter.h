#ifndef FILTER_H
#define FILTER_H

#ifdef _WIN32
#define DLL_EXPORT __declspec(dllexport)
#else
#define DLL_EXPORT
#endif

#ifdef __cplusplus
extern "C" {
#endif

DLL_EXPORT void moving_average_filter(const double* input, double* output, int length, int window_size);

#ifdef __cplusplus
}
#endif

#endif
