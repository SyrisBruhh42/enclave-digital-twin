shader_type canvas_item;
render_mode blend_mix;

// Textures
uniform sampler2D elevation_map : filter_nearest, repeat_disable;
uniform sampler2D palette_lut : filter_nearest, repeat_disable;
uniform sampler2D los_visibility_map : filter_linear, repeat_disable;

// Environment and Lighting Parameters
uniform float ambient_light_level : hint_range(0.0, 1.0) = 0.25;
uniform vec4 chasm_tint : source_color = vec4(0.05, 0.08, 0.15, 1.0);
uniform vec4 peak_tint : source_color = vec4(1.0, 0.95, 0.85, 1.0);
uniform vec2 light_direction = vec2(0.7071, -0.7071);
uniform float edge_highlight_strength : hint_range(0.0, 2.0) = 0.75;

// Number of discrete elevation layers in LUT (e.g., 5 tiers: -2, -1, 0, +1, +2)
const float TOTAL_ELEVATION_TIERS = 5.0;

void fragment() {
    vec4 base_color = texture(TEXTURE, UV);
    
    // Guard against fully transparent pixels
    if (base_color.a < 0.01) {
        discard;
    }

    // Sample discrete elevation value from red channel:
    // Mapped: 0.0 -> Z: -2 | 0.25 -> Z: -1 | 0.5 -> Z: 0 | 0.75 -> Z: +1 | 1.0 -> Z: +2
    float elevation_raw = texture(elevation_map, UV).r;
    float tier_index = floor(elevation_raw * (TOTAL_ELEVATION_TIERS - 1.0) + 0.5);
    float normalized_tier = tier_index / (TOTAL_ELEVATION_TIERS - 1.0);

    // Sample continuous Cellular Line-of-Sight visibility
    float los_visibility = texture(los_visibility_map, UV).r;
    
    // Compute total illumination factor (Ambient + LoS Light contribution)
    float total_light = clamp(ambient_light_level + (los_visibility * (1.0 - ambient_light_level)), 0.0, 1.0);

    // Calculate LUT coordinates:
    // U = Illumination intensity (continuous along width)
    // V = Elevation tier index (discrete row selection centered on pixel center)
    float lut_u = clamp(total_light, 0.005, 0.995);
    float lut_v = (tier_index + 0.5) / TOTAL_ELEVATION_TIERS;
    vec4 graded_color = texture(palette_lut, vec2(lut_u, lut_v));

    // Directional edge highlight for elevated cliffs and pillars (Z >= +1)
    float h_sample_step = TEXTURE_PIXEL_SIZE.x * 1.5;
    float v_sample_step = TEXTURE_PIXEL_SIZE.y * 1.5;
    float elev_offset = texture(elevation_map, UV - (light_direction * vec2(h_sample_step, v_sample_step))).r;
    float edge_delta = max(0.0, elevation_raw - elev_offset);
    
    vec3 final_rgb = graded_color.rgb * base_color.rgb;

    // Apply elevation atmospheric depth tinting
    if (tier_index < 2.0) {
        // Chasms and Depths (Z = -2, -1): Apply cold desaturated tinting
        float depth_factor = (2.0 - tier_index) / 2.0;
        final_rgb = mix(final_rgb, final_rgb * chasm_tint.rgb, depth_factor * 0.75);
    } else if (tier_index > 2.0) {
        // High Bridges and Pillars (Z = +1, +2): Apply warm highlights and rim edges
        float height_factor = (tier_index - 2.0) / 2.0;
        final_rgb = mix(final_rgb, final_rgb * peak_tint.rgb, height_factor * 0.35);
        final_rgb += vec3(edge_delta * edge_highlight_strength * los_visibility);
    }

    COLOR = vec4(final_rgb, base_color.a);
}
