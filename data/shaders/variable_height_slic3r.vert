#version 110

//original author Vojtech Bubnik for Slic3r PrusaResearch edition
//changes by Tibor Vavra for PrusaControl


#define LIGHT_TOP_DIR        0., 1., 0.
#define LIGHT_TOP_DIFFUSE    0.2
#define LIGHT_TOP_SPECULAR   0.3

#define LIGHT_FRONT_DIR      0., 0., 1.
#define LIGHT_FRONT_DIFFUSE  0.5
#define LIGHT_FRONT_SPECULAR 0.3

#define INTENSITY_AMBIENT    0.1

uniform float z_to_texture_row;
uniform float height_of_object;
varying float intensity_specular;
varying float intensity_tainted;
varying float object_z;
varying float z_position;


void main()
{
   vec3 eye, normal, lightDir, viewVector, halfVector;
   float NdotL, NdotHV;

//    eye = gl_ModelViewMatrixInverse[3].xyz;
   eye = vec3(0., 0., 1.);

   // First transform the normal into eye space and normalize the result.
   normal = normalize(gl_NormalMatrix * gl_Normal);

   // Now normalize the light's direction. Note that according to the OpenGL specification, the light is stored in eye space.
   // Also since we're talking about a directional light, the position field is actually direction.
   lightDir = vec3(LIGHT_TOP_DIR);
   halfVector = normalize(lightDir + eye);

   // Compute the cos of the angle between the normal and lights direction. The light is directional so the direction is constant for every vertex.
   // Since these two are normalized the cosine is the dot product. We also need to clamp the result to the [0,1] range.
   NdotL = max(dot(normal, lightDir), 0.0);

   intensity_tainted = INTENSITY_AMBIENT + NdotL * LIGHT_TOP_DIFFUSE;
   intensity_specular = 0.;

//    if (NdotL > 0.0)
//        intensity_specular = LIGHT_TOP_SPECULAR * pow(max(dot(normal, halfVector), 0.0), gl_FrontMaterial.shininess);

   // Perform the same lighting calculation for the 2nd light source.
   lightDir = vec3(LIGHT_FRONT_DIR);
   halfVector = normalize(lightDir + eye);
   NdotL = max(dot(normal, lightDir), 0.0);
   intensity_tainted += NdotL * LIGHT_FRONT_DIFFUSE;

   // compute the specular term if NdotL is larger than zero
   if (NdotL > 0.0)
       intensity_specular += LIGHT_FRONT_SPECULAR * pow(max(dot(normal, halfVector), 0.0), gl_FrontMaterial.shininess);

   // Scaled to widths of the Z texture.
   object_z = gl_Vertex.z / gl_Vertex.w;
   gl_Position = ftransform();
}