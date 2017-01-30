#version 110

//original author Vojtech Bubnik for Slic3r PrusaResearch edition
//changes by Tibor Vavra for PrusaControl

#define M_PI 3.1415926535897932384626433832795

// 2D texture (1D texture split by the rows) of color along the object Z axis.
uniform sampler2D z_texture;
// Scaling from the Z texture rows coordinate to the normalized texture row coordinate.
uniform float z_to_texture_row;
uniform float z_texture_row_to_normalized;
uniform float height_of_object;

varying float intensity_specular;
varying float intensity_tainted;
varying float object_z;
varying float z_position;
uniform float z_cursor;
uniform float z_cursor_band_width;

void main()
{
   //float object_z_row = (z_to_texture_row * object_z) + height_of_object;
   //float object_z_row = z_to_texture_row * (object_z + height_of_object*.5);
   float object_z_row = z_to_texture_row * object_z;
   // Index of the row in the texture.
   float z_texture_row = floor(object_z_row);
   // Normalized coordinate from 0. to 1.
   float z_texture_col = object_z_row - z_texture_row;
//    float z_blend = 0.5 + 0.5 * cos(min(M_PI, abs(M_PI * (object_z - z_cursor) / 3.)));
//    float z_blend = 0.5 * cos(min(M_PI, abs(M_PI * (object_z - z_cursor)))) + 0.5;
   float z_blend = 0.25 * cos(min(M_PI, abs(M_PI * (object_z + height_of_object*.5 - z_cursor) * 1.8 / z_cursor_band_width))) + 0.25;

   // Scale z_texture_row to normalized coordinates.
   // Sample the Z texture.
   gl_FragColor =
       vec4(intensity_specular, intensity_specular, intensity_specular, 1.) +
 //       intensity_tainted * texture2D(z_texture, vec2(z_texture_col, z_texture_row_to_normalized * (z_texture_row + 0.5)), -2.5);
 //      (1. - z_blend) * intensity_tainted * texture2D(z_texture, vec2(z_texture_col, z_texture_row_to_normalized * (z_texture_row + 0.5)), -200.) +
       (1. - z_blend) * intensity_tainted * texture2D(z_texture, vec2(0.01, (object_z-height_of_object*.5)/height_of_object), 0.) +
       z_blend * vec4(1., 1., 0., 0.);

   // and reset the transparency.
   gl_FragColor.a = 1.;
}