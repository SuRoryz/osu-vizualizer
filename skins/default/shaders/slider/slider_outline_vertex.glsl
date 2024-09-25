#version 330 core

// Input vertex position (location = 0)
layout(location = 0) in vec2 a_position;

// Uniforms
uniform mat4 u_mvp_matrix;

void main()
{
    gl_Position = u_mvp_matrix * vec4(a_position, 0.0, 1.0);
}
