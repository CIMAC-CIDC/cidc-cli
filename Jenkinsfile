def label = "worker-${UUID.randomUUID().toString()}"

podTemplate(label: label, namespace: "jenkins", containers: [
  containerTemplate(name: 'python', image: 'python:3.5.1', command: 'cat', ttyEnabled: true)
]) {
  node(label) {
    def myRepo = checkout scm
    stage('Build Docker image') {
      container('python') {
        git 'https://github.com/dfci/cidc-cli.git'
        sh 'python --version'
        sh 'ls -a'
      }
    }
  }
}
