#version 330 core

uniform float u_time;

in vec2 v_tex_coord;
out vec4 frag_color;

// Helper function to convert HSV to RGB
vec3 hsv2rgb(vec3 c)
{
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main()
{
    // Cool shader effect (e.g., moving gradient)
    float hue = mod(v_tex_coord.x + v_tex_coord.y + u_time * 0.0001, 1.0);
    vec3 color = hsv2rgb(vec3(hue, 0.5, 0.5));

    frag_color = vec4(color, 0.1); // 0.2 opacity
}