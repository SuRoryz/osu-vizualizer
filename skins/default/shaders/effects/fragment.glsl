#version 330 core

uniform float u_time;

out vec4 frag_color;

void main()
{
    // Cool hit effect shader (e.g., radial gradient with pulse)
    float dist = length(gl_PointCoord - vec2(0.5));
    float intensity = sin(u_time * 10.0) * 0.5 + 0.5;
    vec3 color = vec3(1.0, 1.0, 1.0) * (1.0 - dist) * intensity;

    frag_color = vec4(color, 1.0 - dist);
}
