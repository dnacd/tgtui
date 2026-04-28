use anyhow::{Context, Result};
use image::imageops::FilterType;
use image::{imageops, GenericImageView, Rgba, RgbaImage};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

#[pyfunction(signature = (data, cols, bright=1.1, sat=1.1, contrast=1.2, _ascii_map=None))]
fn render_to_ansi(
    _py: Python<'_>,
    data: &Bound<'_, PyBytes>,
    cols: u32,
    bright: f32,
    sat: f32,
    contrast: f32,
    _ascii_map: Option<&str>,
) -> PyResult<String> {
    let bytes = data.as_bytes();
    let img = image::load_from_memory(bytes)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    
    let (w0, h0) = img.dimensions();
    let aspect = h0 as f32 / w0 as f32;
    
    let out_w = cols.clamp(8, 160);
    let out_h_chars = (out_w as f32 * aspect * 0.5).round() as u32;
    let out_h_pixels = out_h_chars * 2;

    let mut rgba = img.to_rgba8();
    boost_rgba_inplace(&mut rgba, bright, sat, contrast);
    
    let final_img = imageops::resize(&rgba, out_w, out_h_pixels, FilterType::Lanczos3);

    let mut out = String::with_capacity((out_w * out_h_chars * 40) as usize);
    for y in (0..final_img.height().saturating_sub(1)).step_by(2) {
        for x in 0..out_w {
            let t = final_img.get_pixel(x, y);
            let b = final_img.get_pixel(x, y + 1);
            
            // Format: ESC[38;2;R;G;Bm (foreground) ESC[48;2;R;G;Bm (background) ▀
            out.push_str(&format!(
                "\x1b[38;2;{};{};{};48;2;{};{};{}m▀",
                t[0], t[1], t[2],
                b[0], b[1], b[2]
            ));
        }
        out.push_str("\x1b[0m\n");
    }
    Ok(out)
}

#[pymodule]
fn ascii_render_native(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(render_to_ansi, m)?)?;
    Ok(())
}

fn luma_u8(r: u8, g: u8, b: u8) -> u8 {
    (0.2126 * r as f32 + 0.7152 * g as f32 + 0.0722 * b as f32) as u8
}

fn boost_rgba_inplace(img: &mut RgbaImage, bright: f32, sat: f32, contrast: f32) {
    for p in img.pixels_mut() {
        let mut r = p[0] as f32 / 255.0;
        let mut g = p[1] as f32 / 255.0;
        let mut b = p[2] as f32 / 255.0;

        // Apply contrast
        r = (r - 0.5) * contrast + 0.5;
        g = (g - 0.5) * contrast + 0.5;
        b = (b - 0.5) * contrast + 0.5;

        // Apply brightness
        r *= bright; g *= bright; b *= bright;

        // Clamping
        r = r.clamp(0.0, 1.0); g = g.clamp(0.0, 1.0); b = b.clamp(0.0, 1.0);

        // Apply saturation
        let y = luma_u8((r * 255.0) as u8, (g * 255.0) as u8, (b * 255.0) as u8) as f32 / 255.0;
        r = y + (r - y) * sat;
        g = y + (g - y) * sat;
        b = y + (b - y) * sat;

        p[0] = (r.clamp(0.0, 1.0) * 255.0) as u8;
        p[1] = (g.clamp(0.0, 1.0) * 255.0) as u8;
        p[2] = (b.clamp(0.0, 1.0) * 255.0) as u8;
    }
}
