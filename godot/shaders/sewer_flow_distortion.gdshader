shader_type canvas_item;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D flow_map : filter_linear;
uniform float time_scale = 1.0;
uniform float distortion_strength = 0.05;
uniform float global_alpha = 1.0; // AX-2 Quiet HUD support (fade to 30% idle)

void fragment() {
	vec4 flow_data = texture(flow_map, UV);
	vec2 flow_dir = (flow_data.xy * 2.0) - 1.0;
	float flow_intensity = flow_data.z;
	
	float ripple = sin((UV.x * flow_dir.x + UV.y * flow_dir.y) * 20.0 - TIME * time_scale);
	
	vec2 offset = flow_dir * ripple * distortion_strength * flow_intensity;
	
	vec4 refracted_color = texture(screen_texture, SCREEN_UV + offset);
	refracted_color.a *= global_alpha; // AX-2 support
	
	COLOR = refracted_color;
}
