#version 330 core

uniform float u_time;

out vec4 frag_color;

void main()
{
    // Vortex effect
    vec2 coord = gl_FragCoord.xy / vec2(800.0, 600.0); // Assuming window size
    coord -= 0.5;
    float angle = atan(coord.y, coord.x) + u_time;
    float radius = length(coord);
    float value = sin(10.0 * radius - u_time * 5.0);

    vec3 color = vec3(0.5 + 0.5 * sin(angle * 5.0), 0.5 + 0.5 * cos(angle * 5.0), 0.5);

    frag_color = vec4(color * value, 1.0);
}
