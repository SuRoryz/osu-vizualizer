#version 330 core

out vec4 FragColor;

uniform float u_opacity;

const vec3 slider_color = vec3(0.1, 0.1, 0.1); // Orange color

void main()
{
    FragColor = vec4(slider_color, u_opacity);
}