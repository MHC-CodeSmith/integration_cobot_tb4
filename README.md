# Cobot + TurtleBot4 Integration Overlay

Terceira camada para visualizar TurtleBot4 e MyCobot no mesmo referencial, sem alterar os workspaces existentes.

## Ideia

- TurtleBot4 continua rodando como hoje: ROS 2 Jazzy, Gazebo Harmonic, Nav2, FastDDS.
- MyCobot continua rodando como hoje: ROS 2 Galactic, MoveIt, CycloneDDS, bridge no Jetson Nano.
- Este overlay só adiciona:
  - `map -> mycobot_base_link` fixo em `x=-0.338416188955307`, `y=1.1060110330581665`, `z=0.80`;
  - uma mesa visual nessa posição;
  - o modelo URDF do MyCobot no RViz do lado Jazzy;
  - espelhamento de `/joint_states` do MyCobot via UDP para visualizacao no grafo Jazzy.

## Coordenada de ancoragem

```text
map
└── mycobot_base_link
    x:   -0.338416188955307
    y:    1.1060110330581665
    z:    0.80
    yaw:  0.0
```

`z=0.80` representa a altura do tampo da mesa. A mesa publicada pelo overlay fica com topo nesse Z.

## Uso rapido

1. Inicie o TurtleBot4 exatamente como ja funciona:

```bash
cd /home/mhc/Germany/turtlebot4_jazzy_docker
./run_lab_world.sh true true 0.0 0.0 0.0
```

2. Em outro terminal, lance o overlay. Se o TurtleBot4 estiver rodando no host, use:

```bash
cd /home/mhc/Germany/cobot_tb4_integration
./scripts/run_host_overlay.sh start
```

Esse comando tambem inicia a ponte de juntas reais:

```text
Galactic/container /joint_states -> UDP -> Jazzy/host /mycobot/joint_states
```

Se o TurtleBot4 estiver rodando dentro do container `tb4_sim`, use:

```bash
cd /home/mhc/Germany/cobot_tb4_integration
./scripts/install_overlay_into_tb4_container.sh
./scripts/launch_overlay_in_tb4_container.sh static
```

3. No RViz do TurtleBot4, use `Fixed Frame = map` e adicione:

- `TF`
- `MarkerArray` em `/cobot_tb4_overlay/markers`
- `RobotModel` usando `/mycobot/robot_description` se quiser ver o URDF do MyCobot no mesmo RViz.

## Segunda janela 3D

Com o TurtleBot4/Nav2 ja rodando no host, abra uma janela RViz separada para inspecao 3D:

```bash
cd /home/mhc/Germany/cobot_tb4_integration
./scripts/run_3d_view.sh
```

Esse comando:

- le o mapa ativo em `/map_server yaml_filename`;
- gera obstaculos 3D de 80 cm a partir das celulas ocupadas do mapa salvo;
- garante a ancora do MyCobot em `map -> mycobot_base_link`;
- reinicia a ponte de juntas reais do MyCobot, se o container `mycobot_ros2` estiver ativo;
- abre um novo RViz com TurtleBot4, MyCobot e obstaculos 3D.

## Ponte das juntas do MyCobot

Para gerenciar apenas a ponte que faz o braco 3D acompanhar o estado real/controlado pelo MoveIt:

```bash
cd /home/mhc/Germany/cobot_tb4_integration
./scripts/start_mycobot_joint_exporter.sh status
./scripts/start_mycobot_joint_exporter.sh start
./scripts/start_mycobot_joint_exporter.sh stop
```

Essa ponte nao usa bridge ROS entre Galactic e Jazzy. Ela manda somente `sensor_msgs/JointState` em JSON por UDP e republica em `/mycobot/joint_states` no Jazzy. Controle continua no MoveIt original.

## Limites desta primeira camada

- Nao muda Nav2, Gazebo ou missões do TurtleBot4.
- Nao muda MoveIt, bridge ou visual servoing do MyCobot.
- A visualizacao do MyCobot no Gazebo ainda e tratada como proxima fase. Esta camada ja cria o frame correto e o modelo no RViz, que e o caminho mais seguro para integrar sem misturar distros ROS.
