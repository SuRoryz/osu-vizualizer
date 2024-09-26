#version 330 core
in vec2 v_position;
out vec4 frag_color;

uniform float u_time;

void main()
{
    // Calculate color based on position and time
    float hue = mod(v_position.x / 100.0 + u_time / 5.0, 1.0);
    float r = abs(hue * 6.0 - 3.0) - 1.0;
    float g = 2.0 - abs(hue * 6.0 - 2.0);
    float b = 2.0 - abs(hue * 6.0 - 4.0);
    vec3 color = clamp(vec3(r, g, b), 0.0, 1.0);

    frag_color = vec4(color, 1.0);
}