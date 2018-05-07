// podTemplate(label: 'docker',
//   containers: [containerTemplate(name: 'docker', image: 'docker:1.11', ttyEnabled: true, command: 'cat')],
//   volumes: [hostPathVolume(hostPath: '/var/run/docker.sock', mountPath: '/var/run/docker.sock')],
//   namespace: 'jenkins'
//   ) {

//   def image = "undivideddocker/"
//   node('jnlp') {
//     stage('Build Docker image') {
//       git 'https://github.com/dfci/cidc-cli.git'
//       container('docker') {
//         sh "docker build -t ${image} ."
//       }
//     }
//   }
// }

pipeline {
    agent { docker { image 'python:3.5.1' } }
    stages {
        stage('build') {
            steps {
                sh 'python --version'
            }
        }
    }
}