#[repr(C)]
pub struct PcmMetrics {
    peak: u32,
    rms: f32,
}

/// Measures a signed, little-endian PCM16 block. A trailing byte is ignored.
///
/// # Safety
/// For a nonempty block, `data` must reference `len` readable, immutable bytes
/// until this function returns.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn lya_pcm16_metrics_v1(data: *const u8, len: usize) -> PcmMetrics {
    if data.is_null() || len < 2 || len > isize::MAX as usize {
        return PcmMetrics { peak: 0, rms: 0.0 };
    }

    // The caller retains the buffer for this call. Reading bytes needs no alignment.
    let block = unsafe { std::slice::from_raw_parts(data, len) };
    let mut peak = 0;
    let mut squared_sum = 0.0_f64;
    for sample in block.chunks_exact(2) {
        let value = i32::from(i16::from_le_bytes([sample[0], sample[1]]));
        peak = peak.max(value.unsigned_abs());
        squared_sum += f64::from(value * value);
    }
    let rms = (squared_sum / (len / 2) as f64).sqrt() as f32;
    PcmMetrics { peak, rms }
}
