#version 330 core
layout(location = 0) in vec2 a_position;
uniform mat4 u_mvp_matrix;
out vec2 v_position;

void main()
{
    gl_Position = u_mvp_matrix * vec4(a_position, 0.0, 1.0);
    v_position = a_position;
}