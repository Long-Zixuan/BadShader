$input v_texcoord0

#include "bgfx_shader.sh"

SAMPLER2D(s_ColorTexture, 1);

#define TRUE  1
#define FALSE 0

// ColorPostProcessing normally tonemaps + grades; replacing it without a
// gamma step makes the whole scene very dark, so do it here.
#define EXPOSURE_BASE 1.12
#define EXPOSURE_LIFT 0.45

// ---------------------------------------------------------------------------
// The mask is stored as a traced polygon instead of a texture: the 26.50
// material system cannot load custom PNGs (texture_path is empty on every
// vanilla material and a bound PNG reads back as the magenta placeholder).
// 209 vertices, normalised image space, y DOWN (same as this pass uv).
// ---------------------------------------------------------------------------

// even-odd crossing test for a single polygon edge (ray towards +x)
float edge(vec2 uv, vec2 a, vec2 b) {
    if ((a.y > uv.y) == (b.y > uv.y)) return 0.0;
    float xCross = a.x + (uv.y - a.y) / (b.y - a.y) * (b.x - a.x);
    return (uv.x < xCross) ? 1.0 : 0.0;
}

// final.fsh:isInBlack()
// TRUE when uv falls inside the silhouette (the black region of the artwork).
int isInBlack(vec2 uv) {
    float crossings = 0.0;
    crossings += edge(uv, vec2(0.60419, 0.03186), vec2(0.62875, 0.04848));
    crossings += edge(uv, vec2(0.62875, 0.04848), vec2(0.64240, 0.06233));
    crossings += edge(uv, vec2(0.64240, 0.06233), vec2(0.64331, 0.06648));
    crossings += edge(uv, vec2(0.64331, 0.06648), vec2(0.66151, 0.08864));
    crossings += edge(uv, vec2(0.66151, 0.08864), vec2(0.67607, 0.09418));
    crossings += edge(uv, vec2(0.67607, 0.09418), vec2(0.68517, 0.10249));
    crossings += edge(uv, vec2(0.68517, 0.10249), vec2(0.70701, 0.09141));
    crossings += edge(uv, vec2(0.70701, 0.09141), vec2(0.72247, 0.09141));
    crossings += edge(uv, vec2(0.72247, 0.09141), vec2(0.73885, 0.09834));
    crossings += edge(uv, vec2(0.73885, 0.09834), vec2(0.74886, 0.10665));
    crossings += edge(uv, vec2(0.74886, 0.10665), vec2(0.76342, 0.12742));
    crossings += edge(uv, vec2(0.76342, 0.12742), vec2(0.77707, 0.15235));
    crossings += edge(uv, vec2(0.77707, 0.15235), vec2(0.78799, 0.18283));
    crossings += edge(uv, vec2(0.78799, 0.18283), vec2(0.79163, 0.19945));
    crossings += edge(uv, vec2(0.79163, 0.19945), vec2(0.79254, 0.22853));
    crossings += edge(uv, vec2(0.79254, 0.22853), vec2(0.80528, 0.26593));
    crossings += edge(uv, vec2(0.80528, 0.26593), vec2(0.80801, 0.28255));
    crossings += edge(uv, vec2(0.80801, 0.28255), vec2(0.81347, 0.29917));
    crossings += edge(uv, vec2(0.81347, 0.29917), vec2(0.82712, 0.38643));
    crossings += edge(uv, vec2(0.82712, 0.38643), vec2(0.83258, 0.46814));
    crossings += edge(uv, vec2(0.83258, 0.46814), vec2(0.83258, 0.54571));
    crossings += edge(uv, vec2(0.83258, 0.54571), vec2(0.83439, 0.55540));
    crossings += edge(uv, vec2(0.83439, 0.55540), vec2(0.83530, 0.64266));
    crossings += edge(uv, vec2(0.83530, 0.64266), vec2(0.83803, 0.68560));
    crossings += edge(uv, vec2(0.83803, 0.68560), vec2(0.84167, 0.69806));
    crossings += edge(uv, vec2(0.84167, 0.69806), vec2(0.84258, 0.71191));
    crossings += edge(uv, vec2(0.84258, 0.71191), vec2(0.84076, 0.71191));
    crossings += edge(uv, vec2(0.84076, 0.71191), vec2(0.83258, 0.69668));
    crossings += edge(uv, vec2(0.83258, 0.69668), vec2(0.83348, 0.69391));
    crossings += edge(uv, vec2(0.83348, 0.69391), vec2(0.83167, 0.69391));
    crossings += edge(uv, vec2(0.83167, 0.69391), vec2(0.83258, 0.69252));
    crossings += edge(uv, vec2(0.83258, 0.69252), vec2(0.82621, 0.68144));
    crossings += edge(uv, vec2(0.82621, 0.68144), vec2(0.82257, 0.66898));
    crossings += edge(uv, vec2(0.82257, 0.66898), vec2(0.81984, 0.66482));
    crossings += edge(uv, vec2(0.81984, 0.66482), vec2(0.81802, 0.66620));
    crossings += edge(uv, vec2(0.81802, 0.66620), vec2(0.81802, 0.67867));
    crossings += edge(uv, vec2(0.81802, 0.67867), vec2(0.81984, 0.68144));
    crossings += edge(uv, vec2(0.81984, 0.68144), vec2(0.82439, 0.72022));
    crossings += edge(uv, vec2(0.82439, 0.72022), vec2(0.82712, 0.72576));
    crossings += edge(uv, vec2(0.82712, 0.72576), vec2(0.82803, 0.73961));
    crossings += edge(uv, vec2(0.82803, 0.73961), vec2(0.82621, 0.73823));
    crossings += edge(uv, vec2(0.82621, 0.73823), vec2(0.81438, 0.70222));
    crossings += edge(uv, vec2(0.81438, 0.70222), vec2(0.81438, 0.69668));
    crossings += edge(uv, vec2(0.81438, 0.69668), vec2(0.81074, 0.69114));
    crossings += edge(uv, vec2(0.81074, 0.69114), vec2(0.79982, 0.64404));
    crossings += edge(uv, vec2(0.79982, 0.64404), vec2(0.79709, 0.63989));
    crossings += edge(uv, vec2(0.79709, 0.63989), vec2(0.79709, 0.65097));
    crossings += edge(uv, vec2(0.79709, 0.65097), vec2(0.80164, 0.67590));
    crossings += edge(uv, vec2(0.80164, 0.67590), vec2(0.80164, 0.69391));
    crossings += edge(uv, vec2(0.80164, 0.69391), vec2(0.80619, 0.71745));
    crossings += edge(uv, vec2(0.80619, 0.71745), vec2(0.80619, 0.72022));
    crossings += edge(uv, vec2(0.80619, 0.72022), vec2(0.80255, 0.71884));
    crossings += edge(uv, vec2(0.80255, 0.71884), vec2(0.80164, 0.72299));
    crossings += edge(uv, vec2(0.80164, 0.72299), vec2(0.80619, 0.73684));
    crossings += edge(uv, vec2(0.80619, 0.73684), vec2(0.80528, 0.73823));
    crossings += edge(uv, vec2(0.80528, 0.73823), vec2(0.80255, 0.73407));
    crossings += edge(uv, vec2(0.80255, 0.73407), vec2(0.79254, 0.69391));
    crossings += edge(uv, vec2(0.79254, 0.69391), vec2(0.78890, 0.68698));
    crossings += edge(uv, vec2(0.78890, 0.68698), vec2(0.78799, 0.67729));
    crossings += edge(uv, vec2(0.78799, 0.67729), vec2(0.78526, 0.67590));
    crossings += edge(uv, vec2(0.78526, 0.67590), vec2(0.78162, 0.68837));
    crossings += edge(uv, vec2(0.78162, 0.68837), vec2(0.78708, 0.78116));
    crossings += edge(uv, vec2(0.78708, 0.78116), vec2(0.79618, 0.80332));
    crossings += edge(uv, vec2(0.79618, 0.80332), vec2(0.79618, 0.81163));
    crossings += edge(uv, vec2(0.79618, 0.81163), vec2(0.78890, 0.81302));
    crossings += edge(uv, vec2(0.78890, 0.81302), vec2(0.78617, 0.80886));
    crossings += edge(uv, vec2(0.78617, 0.80886), vec2(0.77707, 0.77839));
    crossings += edge(uv, vec2(0.77707, 0.77839), vec2(0.76888, 0.77147));
    crossings += edge(uv, vec2(0.76888, 0.77147), vec2(0.76615, 0.77147));
    crossings += edge(uv, vec2(0.76615, 0.77147), vec2(0.76524, 0.77562));
    crossings += edge(uv, vec2(0.76524, 0.77562), vec2(0.76888, 0.79224));
    crossings += edge(uv, vec2(0.76888, 0.79224), vec2(0.77343, 0.84211));
    crossings += edge(uv, vec2(0.77343, 0.84211), vec2(0.77707, 0.85596));
    crossings += edge(uv, vec2(0.77707, 0.85596), vec2(0.77798, 0.88227));
    crossings += edge(uv, vec2(0.77798, 0.88227), vec2(0.78344, 0.90997));
    crossings += edge(uv, vec2(0.78344, 0.90997), vec2(0.78344, 0.92105));
    crossings += edge(uv, vec2(0.78344, 0.92105), vec2(0.78162, 0.92521));
    crossings += edge(uv, vec2(0.78162, 0.92521), vec2(0.78708, 0.94460));
    crossings += edge(uv, vec2(0.78708, 0.94460), vec2(0.79163, 0.99169));
    crossings += edge(uv, vec2(0.79163, 0.99169), vec2(0.79345, 0.99446));
    crossings += edge(uv, vec2(0.79345, 0.99446), vec2(0.80164, 0.99169));
    crossings += edge(uv, vec2(0.80164, 0.99169), vec2(0.80437, 0.98753));
    crossings += edge(uv, vec2(0.80437, 0.98753), vec2(0.84258, 0.96537));
    crossings += edge(uv, vec2(0.84258, 0.96537), vec2(0.85987, 0.97091));
    crossings += edge(uv, vec2(0.85987, 0.97091), vec2(0.86078, 0.97368));
    crossings += edge(uv, vec2(0.86078, 0.97368), vec2(0.84804, 0.98892));
    crossings += edge(uv, vec2(0.84804, 0.98892), vec2(0.85168, 0.99584));
    crossings += edge(uv, vec2(0.85168, 0.99584), vec2(0.84531, 1.00000));
    crossings += edge(uv, vec2(0.84531, 1.00000), vec2(0.34304, 1.00000));
    crossings += edge(uv, vec2(0.34304, 1.00000), vec2(0.34395, 0.96260));
    crossings += edge(uv, vec2(0.34395, 0.96260), vec2(0.35032, 0.92244));
    crossings += edge(uv, vec2(0.35032, 0.92244), vec2(0.34577, 0.91828));
    crossings += edge(uv, vec2(0.34577, 0.91828), vec2(0.34304, 0.91967));
    crossings += edge(uv, vec2(0.34304, 0.91967), vec2(0.34213, 0.91690));
    crossings += edge(uv, vec2(0.34213, 0.91690), vec2(0.32120, 0.91274));
    crossings += edge(uv, vec2(0.32120, 0.91274), vec2(0.31938, 0.90997));
    crossings += edge(uv, vec2(0.31938, 0.90997), vec2(0.30846, 0.90720));
    crossings += edge(uv, vec2(0.30846, 0.90720), vec2(0.29845, 0.90166));
    crossings += edge(uv, vec2(0.29845, 0.90166), vec2(0.28844, 0.89197));
    crossings += edge(uv, vec2(0.28844, 0.89197), vec2(0.26661, 0.85319));
    crossings += edge(uv, vec2(0.26661, 0.85319), vec2(0.26206, 0.83102));
    crossings += edge(uv, vec2(0.26206, 0.83102), vec2(0.26206, 0.81163));
    crossings += edge(uv, vec2(0.26206, 0.81163), vec2(0.25751, 0.79363));
    crossings += edge(uv, vec2(0.25751, 0.79363), vec2(0.25751, 0.77285));
    crossings += edge(uv, vec2(0.25751, 0.77285), vec2(0.26661, 0.73130));
    crossings += edge(uv, vec2(0.26661, 0.73130), vec2(0.28389, 0.71468));
    crossings += edge(uv, vec2(0.28389, 0.71468), vec2(0.30664, 0.70360));
    crossings += edge(uv, vec2(0.30664, 0.70360), vec2(0.30846, 0.70083));
    crossings += edge(uv, vec2(0.30846, 0.70083), vec2(0.30846, 0.67313));
    crossings += edge(uv, vec2(0.30846, 0.67313), vec2(0.31028, 0.67175));
    crossings += edge(uv, vec2(0.31028, 0.67175), vec2(0.31028, 0.68144));
    crossings += edge(uv, vec2(0.31028, 0.68144), vec2(0.31210, 0.68421));
    crossings += edge(uv, vec2(0.31210, 0.68421), vec2(0.31392, 0.69945));
    crossings += edge(uv, vec2(0.31392, 0.69945), vec2(0.33940, 0.69252));
    crossings += edge(uv, vec2(0.33940, 0.69252), vec2(0.34941, 0.69252));
    crossings += edge(uv, vec2(0.34941, 0.69252), vec2(0.35396, 0.69668));
    crossings += edge(uv, vec2(0.35396, 0.69668), vec2(0.36033, 0.69668));
    crossings += edge(uv, vec2(0.36033, 0.69668), vec2(0.35942, 0.69806));
    crossings += edge(uv, vec2(0.35942, 0.69806), vec2(0.37034, 0.71191));
    crossings += edge(uv, vec2(0.37034, 0.71191), vec2(0.37762, 0.73407));
    crossings += edge(uv, vec2(0.37762, 0.73407), vec2(0.38035, 0.75208));
    crossings += edge(uv, vec2(0.38035, 0.75208), vec2(0.38035, 0.80194));
    crossings += edge(uv, vec2(0.38035, 0.80194), vec2(0.38581, 0.80886));
    crossings += edge(uv, vec2(0.38581, 0.80886), vec2(0.39490, 0.82825));
    crossings += edge(uv, vec2(0.39490, 0.82825), vec2(0.40127, 0.82687));
    crossings += edge(uv, vec2(0.40127, 0.82687), vec2(0.40764, 0.82964));
    crossings += edge(uv, vec2(0.40764, 0.82964), vec2(0.44040, 0.84903));
    crossings += edge(uv, vec2(0.44040, 0.84903), vec2(0.45769, 0.85596));
    crossings += edge(uv, vec2(0.45769, 0.85596), vec2(0.46042, 0.86011));
    crossings += edge(uv, vec2(0.46042, 0.86011), vec2(0.47407, 0.86565));
    crossings += edge(uv, vec2(0.47407, 0.86565), vec2(0.47680, 0.86981));
    crossings += edge(uv, vec2(0.47680, 0.86981), vec2(0.49045, 0.87673));
    crossings += edge(uv, vec2(0.49045, 0.87673), vec2(0.50136, 0.88643));
    crossings += edge(uv, vec2(0.50136, 0.88643), vec2(0.50500, 0.88366));
    crossings += edge(uv, vec2(0.50500, 0.88366), vec2(0.53139, 0.83934));
    crossings += edge(uv, vec2(0.53139, 0.83934), vec2(0.53139, 0.78393));
    crossings += edge(uv, vec2(0.53139, 0.78393), vec2(0.53503, 0.77701));
    crossings += edge(uv, vec2(0.53503, 0.77701), vec2(0.54140, 0.77147));
    crossings += edge(uv, vec2(0.54140, 0.77147), vec2(0.55687, 0.77147));
    crossings += edge(uv, vec2(0.55687, 0.77147), vec2(0.56779, 0.77839));
    crossings += edge(uv, vec2(0.56779, 0.77839), vec2(0.57143, 0.77147));
    crossings += edge(uv, vec2(0.57143, 0.77147), vec2(0.57962, 0.73684));
    crossings += edge(uv, vec2(0.57962, 0.73684), vec2(0.58235, 0.73269));
    crossings += edge(uv, vec2(0.58235, 0.73269), vec2(0.58326, 0.72576));
    crossings += edge(uv, vec2(0.58326, 0.72576), vec2(0.57962, 0.70637));
    crossings += edge(uv, vec2(0.57962, 0.70637), vec2(0.57780, 0.67313));
    crossings += edge(uv, vec2(0.57780, 0.67313), vec2(0.57507, 0.66620));
    crossings += edge(uv, vec2(0.57507, 0.66620), vec2(0.57143, 0.66343));
    crossings += edge(uv, vec2(0.57143, 0.66343), vec2(0.57507, 0.65651));
    crossings += edge(uv, vec2(0.57507, 0.65651), vec2(0.57598, 0.63296));
    crossings += edge(uv, vec2(0.57598, 0.63296), vec2(0.56597, 0.63296));
    crossings += edge(uv, vec2(0.56597, 0.63296), vec2(0.57052, 0.59834));
    crossings += edge(uv, vec2(0.57052, 0.59834), vec2(0.57052, 0.57479));
    crossings += edge(uv, vec2(0.57052, 0.57479), vec2(0.55869, 0.55817));
    crossings += edge(uv, vec2(0.55869, 0.55817), vec2(0.55596, 0.54986));
    crossings += edge(uv, vec2(0.55596, 0.54986), vec2(0.55050, 0.54709));
    crossings += edge(uv, vec2(0.55050, 0.54709), vec2(0.54504, 0.52493));
    crossings += edge(uv, vec2(0.54504, 0.52493), vec2(0.53230, 0.51662));
    crossings += edge(uv, vec2(0.53230, 0.51662), vec2(0.52775, 0.50970));
    crossings += edge(uv, vec2(0.52775, 0.50970), vec2(0.52775, 0.50416));
    crossings += edge(uv, vec2(0.52775, 0.50416), vec2(0.53594, 0.49030));
    crossings += edge(uv, vec2(0.53594, 0.49030), vec2(0.53958, 0.47784));
    crossings += edge(uv, vec2(0.53958, 0.47784), vec2(0.53958, 0.45568));
    crossings += edge(uv, vec2(0.53958, 0.45568), vec2(0.53776, 0.45014));
    crossings += edge(uv, vec2(0.53776, 0.45014), vec2(0.53503, 0.44875));
    crossings += edge(uv, vec2(0.53503, 0.44875), vec2(0.53594, 0.45706));
    crossings += edge(uv, vec2(0.53594, 0.45706), vec2(0.53412, 0.45706));
    crossings += edge(uv, vec2(0.53412, 0.45706), vec2(0.52593, 0.43629));
    crossings += edge(uv, vec2(0.52593, 0.43629), vec2(0.52411, 0.44044));
    crossings += edge(uv, vec2(0.52411, 0.44044), vec2(0.52957, 0.45429));
    crossings += edge(uv, vec2(0.52957, 0.45429), vec2(0.53048, 0.46399));
    crossings += edge(uv, vec2(0.53048, 0.46399), vec2(0.51592, 0.44321));
    crossings += edge(uv, vec2(0.51592, 0.44321), vec2(0.51319, 0.44460));
    crossings += edge(uv, vec2(0.51319, 0.44460), vec2(0.50864, 0.43352));
    crossings += edge(uv, vec2(0.50864, 0.43352), vec2(0.50682, 0.43490));
    crossings += edge(uv, vec2(0.50682, 0.43490), vec2(0.50773, 0.44044));
    crossings += edge(uv, vec2(0.50773, 0.44044), vec2(0.50318, 0.43906));
    crossings += edge(uv, vec2(0.50318, 0.43906), vec2(0.49773, 0.41690));
    crossings += edge(uv, vec2(0.49773, 0.41690), vec2(0.49773, 0.43629));
    crossings += edge(uv, vec2(0.49773, 0.43629), vec2(0.49136, 0.41413));
    crossings += edge(uv, vec2(0.49136, 0.41413), vec2(0.48863, 0.42521));
    crossings += edge(uv, vec2(0.48863, 0.42521), vec2(0.48681, 0.42382));
    crossings += edge(uv, vec2(0.48681, 0.42382), vec2(0.48681, 0.39058));
    crossings += edge(uv, vec2(0.48681, 0.39058), vec2(0.48408, 0.37535));
    crossings += edge(uv, vec2(0.48408, 0.37535), vec2(0.48226, 0.37535));
    crossings += edge(uv, vec2(0.48226, 0.37535), vec2(0.48135, 0.38227));
    crossings += edge(uv, vec2(0.48135, 0.38227), vec2(0.47953, 0.38227));
    crossings += edge(uv, vec2(0.47953, 0.38227), vec2(0.48135, 0.36842));
    crossings += edge(uv, vec2(0.48135, 0.36842), vec2(0.47953, 0.36704));
    crossings += edge(uv, vec2(0.47953, 0.36704), vec2(0.47134, 0.37950));
    crossings += edge(uv, vec2(0.47134, 0.37950), vec2(0.46861, 0.37950));
    crossings += edge(uv, vec2(0.46861, 0.37950), vec2(0.47407, 0.36981));
    crossings += edge(uv, vec2(0.47407, 0.36981), vec2(0.47953, 0.35180));
    crossings += edge(uv, vec2(0.47953, 0.35180), vec2(0.48499, 0.29086));
    crossings += edge(uv, vec2(0.48499, 0.29086), vec2(0.48954, 0.27008));
    crossings += edge(uv, vec2(0.48954, 0.27008), vec2(0.50045, 0.24100));
    crossings += edge(uv, vec2(0.50045, 0.24100), vec2(0.51046, 0.22022));
    crossings += edge(uv, vec2(0.51046, 0.22022), vec2(0.53321, 0.18698));
    crossings += edge(uv, vec2(0.53321, 0.18698), vec2(0.55687, 0.16205));
    crossings += edge(uv, vec2(0.55687, 0.16205), vec2(0.56688, 0.15512));
    crossings += edge(uv, vec2(0.56688, 0.15512), vec2(0.57052, 0.14820));
    crossings += edge(uv, vec2(0.57052, 0.14820), vec2(0.56415, 0.12604));
    crossings += edge(uv, vec2(0.56415, 0.12604), vec2(0.56142, 0.10803));
    crossings += edge(uv, vec2(0.56142, 0.10803), vec2(0.56142, 0.07756));
    crossings += edge(uv, vec2(0.56142, 0.07756), vec2(0.56415, 0.06371));
    crossings += edge(uv, vec2(0.56415, 0.06371), vec2(0.57416, 0.04848));
    crossings += edge(uv, vec2(0.57416, 0.04848), vec2(0.58508, 0.04155));
    crossings += edge(uv, vec2(0.58508, 0.04155), vec2(0.59873, 0.03740));
    crossings += edge(uv, vec2(0.59873, 0.03740), vec2(0.60419, 0.03186));
    return (fract(crossings * 0.5) > 0.25) ? TRUE : FALSE;
}

vec3 tonemap(vec3 c) {
    vec3 s = sqrt(max(c, vec3(0.0, 0.0, 0.0)));
    vec3 lift = vec3(EXPOSURE_BASE + EXPOSURE_LIFT * (1.0 - s.x),
                     EXPOSURE_BASE + EXPOSURE_LIFT * (1.0 - s.y),
                     EXPOSURE_BASE + EXPOSURE_LIFT * (1.0 - s.z));
    return clamp(s * lift, vec3(0.0, 0.0, 0.0), vec3(1.0, 1.0, 1.0));
}

void main() {
    vec2 texcoord = v_texcoord0.xy;

    vec4 sceneColor = texture2D(s_ColorTexture, texcoord);
    sceneColor.rgb = tonemap(sceneColor.rgb);

    vec4 color = sceneColor;

    if (isInBlack(texcoord) == TRUE) {
        color.x = 1.0 - color.x;
        color.y = 1.0 - color.y;
        color.z = 1.0 - color.z;
    }

    color.a = 1.0;
    gl_FragColor = color;
}
