shader_type canvas_item;
render_mode blend_mix;

uniform vec2 light_dir = vec2(0.707106, -0.707106); // Default top-right
uniform float bevel_width_px = 1.0;
uniform float rim_intensity = 0.4;
uniform float mortar_darkness = 0.6;
uniform vec2 resolution = vec2(448.0, 998.0); // Native resolution

void fragment() {
    // Basic gl_compatibility safe shader to compute discrete stepped pixel highlights.
    
    // Sample base texture
    vec4 base_color = texture(TEXTURE, UV);
    
    // Compute pixel size
    vec2 pixel_size = vec2(1.0) / resolution;
    vec2 offset = light_dir * (bevel_width_px * pixel_size);
    
    // Simple bevel effect: compare current pixel to offset pixel (if texture allows, otherwise use a simulated bump)
    // We simulate a bump map using luminance of offset samples to give a rough stone look.
    float lum_center = dot(base_color.rgb, vec3(0.299, 0.587, 0.114));
    
    vec4 offset_color = texture(TEXTURE, UV - offset);
    float lum_offset = dot(offset_color.rgb, vec3(0.299, 0.587, 0.114));
    
    // Discrete stepped highlight
    float diff = lum_offset - lum_center;
    float highlight = step(0.05, diff) * rim_intensity;
    float shadow = step(0.05, -diff) * mortar_darkness;
    
    vec3 final_color = base_color.rgb + vec3(highlight) - vec3(shadow);
    
    // Clamp and output
    COLOR = vec4(clamp(final_color, 0.0, 1.0), base_color.a);
    
    // AX-2 & AX-3 invariants are generally handled by UI logic, but this shader handles the visual style of rough stone.
}
