#version 110
#define M_PI 3.1415926535897932384626433832795

varying float object_z;

void main()
{
   float layer_height = 0.03;
   float layer_height2 = 0.5 * layer_height;
   float layer_center = floor(object_z / layer_height) * layer_height + layer_height2;
   float intensity = cos(M_PI * 0.7 * (layer_center - object_z) / layer_height);
   gl_FragColor = gl_Color * intensity;
   gl_FragColor.a = 1.;
}