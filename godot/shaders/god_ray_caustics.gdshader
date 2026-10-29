shader_type canvas_item;

uniform vec4 ray_color : source_color = vec4(1.0, 0.9, 0.7, 1.0);
uniform float intensity : hint_range(0.0, 5.0) = 1.0;
uniform float time_scale = 1.0;
uniform float idle_time = 0.0;

// AX-2: HUD fade. After 4.0s idle, max alpha is 0.3
void fragment() {
    // Generate basic moving god rays using UV and TIME
    vec2 uv = UV;
    float ray = sin(uv.x * 10.0 + TIME * time_scale) * 0.5 + 0.5;
    ray *= sin(uv.y * 5.0 - TIME * time_scale * 0.5) * 0.5 + 0.5;
    
    // Falloff towards edges
    float falloff = smoothstep(0.0, 0.2, uv.x) * smoothstep(1.0, 0.8, uv.x);
    
    vec4 final_color = ray_color * ray * intensity * falloff;
    
    // AX-2 requirement: HUD fade to 30% alpha at 4.0s idle.
    // If idle_time >= 4.0, target max alpha is 0.3.
    // We linearly interpolate max alpha between 1.0 (at < 4.0) to 0.3 (at 4.0).
    float max_alpha = 1.0;
    if (idle_time >= 4.0) {
        max_alpha = 0.3;
    }
    
    // Enforce AX-3 requirement inside UI logic, but here in shader we'll just respect HUD fade.
    final_color.a = clamp(final_color.a, 0.0, max_alpha);
    
    COLOR = final_color;
}
