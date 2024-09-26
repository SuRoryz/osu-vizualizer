#version 330 core

layout(location = 0) in vec2 a_position;

out vec2 v_tex_coord;

void main()
{
    gl_Position = vec4(a_position, 0.0, 1.0);
    v_tex_coord = a_position * 0.5 + 0.5; // Map to [0, 1]
}