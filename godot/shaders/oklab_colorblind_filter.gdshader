shader_type canvas_item;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;

uniform mat3 sim_mat;
uniform mat3 shift_mat;
uniform mat3 oklab_m1;
uniform mat3 oklab_m2;
uniform mat3 oklab_m1_inv;
uniform mat3 oklab_m2_inv;

vec3 srgb_to_linear(vec3 rgb) {
    vec3 cutoff = step(rgb, vec3(0.04045));
    vec3 higher = pow((rgb + vec3(0.055)) / vec3(1.055), vec3(2.4));
    vec3 lower = rgb / vec3(12.92);
    return mix(higher, lower, step(rgb, vec3(0.04045)));
}

vec3 linear_to_srgb(vec3 lin) {
    vec3 higher = vec3(1.055) * pow(lin, vec3(1.0 / 2.4)) - vec3(0.055);
    vec3 lower = lin * vec3(12.92);
    
    vec3 result = mix(higher, lower, step(lin, vec3(0.0031308)));
    return clamp(result, vec3(0.0), vec3(1.0));
}

vec3 linear_to_oklab(vec3 lin) {
    vec3 lms = oklab_m1 * lin;
    lms = max(lms, vec3(0.0));
    vec3 lms_cbrt = pow(lms, vec3(1.0 / 3.0));
    return oklab_m2 * lms_cbrt;
}

vec3 oklab_to_linear(vec3 ok) {
    vec3 lms_cbrt = oklab_m2_inv * ok;
    lms_cbrt = max(lms_cbrt, vec3(0.0));
    vec3 lms = pow(lms_cbrt, vec3(3.0));
    return oklab_m1_inv * lms;
}

void fragment() {
    vec4 tex_color = texture(screen_texture, SCREEN_UV);
    vec3 srgb = tex_color.rgb;
    
    vec3 lin_orig = srgb_to_linear(srgb);
    vec3 lin_sim = sim_mat * lin_orig;
    
    vec3 ok_orig = linear_to_oklab(lin_orig);
    vec3 ok_sim = linear_to_oklab(lin_sim);
    
    vec3 ok_err = ok_orig - ok_sim;
    vec3 ok_shift = shift_mat * ok_err;
    
    vec3 ok_dalton = ok_orig + ok_shift;
    ok_dalton.y -= ok_err.y * 0.75;
    
    vec3 lin_dalton = oklab_to_linear(ok_dalton);
    vec3 srgb_dalton = linear_to_srgb(lin_dalton);
    
    COLOR = vec4(srgb_dalton, tex_color.a);
}
