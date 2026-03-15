#include "filter.h"

void moving_average_filter(const double* input, double* output, int length, int window_size) {
    if (window_size % 2 == 0) {
        window_size++;
    }
    
    int half_window = window_size / 2;
    
    for (int i = 0; i < length; i++) {
        double sum = 0.0;
        int count = 0;
        
        for (int j = -half_window; j <= half_window; j++) {
            int idx = i + j;
            if (idx >= 0 && idx < length) {
                sum += input[idx];
                count++;
            }
        }
        
        output[i] = sum / count;
    }
}
