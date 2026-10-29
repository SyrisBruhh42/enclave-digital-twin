shader_type canvas_item;
render_mode blend_mix;

uniform sampler2D emissive_texture : hint_default_black, filter_linear_mipmap;
uniform vec4 rim_color_cool : source_color = vec4(0.847, 0.925, 1.0, 1.0);     // #D8ECFF
uniform vec4 rim_color_warm : source_color = vec4(0.384, 0.949, 0.710, 1.0);    // #62F2B5
uniform vec4 emissive_tint_core : source_color = vec4(0.0, 1.0, 0.4, 1.0);     // #00FF66
uniform vec4 emissive_tint_trim : source_color = vec4(0.0, 0.898, 1.0, 1.0);    // #00E5FF
uniform float breathing_cycle_sec : hint_range(4.0, 12.0) = 8.0;
uniform float rim_thickness : hint_range(0.5, 4.0) = 1.5;
uniform float mouse_light_intensity : hint_range(0.0, 2.0) = 0.8;
uniform vec2 mouse_screen_pos = vec2(0.5, 0.5);

void fragment() {
    vec4 albedo = texture(TEXTURE, UV);
    if (albedo.a < 0.02) {
        discard;
    }

    // 1. Unmix remaining white spill on semi-transparent edges
    float alpha = albedo.a;
    if (alpha < 0.98) {
        albedo.rgb = clamp((albedo.rgb - vec3(1.0) * (1.0 - alpha)) / max(alpha, 0.15), vec3(0.0), vec3(1.0));
    }

    // 2. Normal reconstruction (+Y OpenGL convention)
    vec3 normal_raw = texture(NORMAL_TEXTURE, UV).rgb;
    vec3 normal = normalize(normal_raw * 2.0 - 1.0);

    // 3. Silhouette Edge Rim Lighting (Sobel in UV space)
    vec2 tex_step = TEXTURE_PIXEL_SIZE * rim_thickness;
    float a_up    = texture(TEXTURE, UV + vec2(0.0, -tex_step.y)).a;
    float a_down  = texture(TEXTURE, UV + vec2(0.0, tex_step.y)).a;
    float a_left  = texture(TEXTURE, UV + vec2(-tex_step.x, 0.0)).a;
    float a_right = texture(TEXTURE, UV + vec2(tex_step.x, 0.0)).a;

    vec2 grad = vec2(a_right - a_left, a_down - a_up);
    float edge_factor = clamp(length(grad) * 2.5 * (1.0 - alpha), 0.0, 1.0);
    vec2 edge_normal = length(grad) > 0.001 ? -normalize(grad) : vec2(0.0);

    vec2 moon_dir = normalize(vec2(-0.707, -0.707));
    vec2 ground_bounce_dir = normalize(vec2(0.707, 0.707));
    float rim_moon = max(0.0, dot(edge_normal, moon_dir)) * edge_factor;
    float rim_bounce = max(0.0, dot(edge_normal, ground_bounce_dir)) * edge_factor;

    vec3 rim_contribution = (rim_color_cool.rgb * rim_moon * 1.1) + (rim_color_warm.rgb * rim_bounce * 0.75);

    // 4. Bi-Zone Emissive Bioluminescence with Asymmetric Breathing Curve
    vec4 em_tex = texture(emissive_texture, UV);
    float breath_phase = TIME * (2.0 * PI / breathing_cycle_sec);
    float breath_pulse = pow(0.5 + 0.5 * sin(breath_phase), 1.4);

    float is_core = step(0.05, em_tex.g - em_tex.b);
    vec3 em_color = is_core > 0.5
        ? (emissive_tint_core.rgb * (1.0 + breath_pulse * 0.35))
        : (emissive_tint_trim.rgb * (1.0 + sin(breath_phase + UV.y * 4.0) * 0.18));

    vec3 emissive = em_tex.rgb * em_color * 1.8;

    // 5. Specular Sheen from Virtual Cursor Light
    vec2 light_dir_2d = mouse_screen_pos - UV;
    vec3 light_vec = normalize(vec3(light_dir_2d, 0.35));
    vec3 half_vec = normalize(light_vec + vec3(0.0, 0.0, 1.0));
    float spec_factor = pow(max(0.0, dot(normal, half_vec)), 32.0);
    vec3 spec = vec3(spec_factor) * mouse_light_intensity * (1.0 - albedo.r * 0.4);

    COLOR = vec4(albedo.rgb + rim_contribution + emissive + spec, alpha);
    NORMAL = normal;
}
