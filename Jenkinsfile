def label = "worker-${UUID.randomUUID().toString()}"

podTemplate(label: label, namespace: "jenkins", containers: [
  containerTemplate(name: 'python', image: 'python:3.5.1', command: 'cat', ttyEnabled: true)
]) {
  node(label) {
    stage('Build Docker image') {
      container('python') {
        checkout scm
        sh 'python --version'
        sh 'ls'
        sh 'pip install -r requirements.txt --no-index'
        sh 'nose2'
      }
    }
  }
}
