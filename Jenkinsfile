def label = "worker-${UUID.randomUUID().toString()}"

podTemplate(label: label, namespace: "jenkins", containers: [
  containerTemplate(name: 'python', image: 'python:3.6.5', command: 'cat', ttyEnabled: true)
]) {
  node(label) {
    stage('Run unit tests') {
      container('python') {
        checkout scm
        sh 'python --version'
        sh 'ls'
        sh 'pip3 install -r requirements.txt'
        sh 'nose2'
      }
    }
  }
}
