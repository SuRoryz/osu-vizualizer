#version 330 core

layout(location = 0) in vec2 a_position;
layout(location = 1) in float a_width;

uniform mat4 u_mvp_matrix;

out float v_width;

void main()
{
    gl_Position = u_mvp_matrix * vec4(a_position, 0.0, 1.0);
    v_width = a_width;
}