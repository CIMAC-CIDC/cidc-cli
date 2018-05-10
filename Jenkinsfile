podTemplate(
  label: 'docker',
  containers: [
      containerTemplate(name: 'cli', image: 'python:3.5.1', ttyEnabled: true, command: 'cat')
      ],
  volumes: [hostPathVolume(hostPath: '/var/run/docker.sock', mountPath: '/var/run/docker.sock')],
  namespace: 'jenkins'
  ) {
  node {
    def myRepo = checkout scm
    stage('Build Docker image') {
      git 'https://github.com/dfci/cidc-cli.git'
      container('docker') {
        sh "python --version"
      }
    }
  }
}